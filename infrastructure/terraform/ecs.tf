resource "aws_security_group" "ecs" {
  name   = "${local.project}-ecs-sg"
  vpc_id = aws_vpc.main.id

  ingress {
    from_port       = 8000
    to_port         = 8010
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${local.project}-ecs-sg" }
}

resource "aws_ecs_cluster" "main" {
  name = "${local.project}-prod"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

resource "aws_cloudwatch_log_group" "ecs" {
  name              = "/ecs/${local.project}"
  retention_in_days = 30
}

resource "aws_iam_role" "task_exec" {
  name = "${local.project}-ecs-exec-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "task_exec" {
  role       = aws_iam_role.task_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "secrets_access" {
  name = "${local.project}-secrets"
  role = aws_iam_role.task_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = ["secretsmanager:GetSecretValue"]
      Resource = [
        aws_secretsmanager_secret.jwt.arn,
        aws_secretsmanager_secret.anthropic.arn,
        aws_secretsmanager_secret.alpha_vantage.arn,
      ]
    }]
  })
}

resource "aws_iam_role" "task" {
  name = "${local.project}-ecs-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

# ─── auth ──────────────────────────────────────────────────────

resource "aws_ecs_task_definition" "auth" {
  family                   = "${local.project}-auth"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "512"
  memory                   = "1024"
  execution_role_arn       = aws_iam_role.task_exec.arn
  task_role_arn            = aws_iam_role.task.arn

  container_definitions = jsonencode([{
    name      = "auth"
    image     = "${aws_ecr_repository.services["auth"].repository_url}:latest"
    essential = true
    portMappings = [{ containerPort = 8000 }]
    environment = [
      { name = "ENVIRONMENT",  value = "production" },
      { name = "DATABASE_URL", value = local.auth_db_url },
      { name = "REDIS_URL",    value = local.redis_url },
    ]
    secrets = [
      { name = "JWT_SECRET_KEY", valueFrom = aws_secretsmanager_secret.jwt.arn }
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.ecs.name
        "awslogs-region"        = local.region
        "awslogs-stream-prefix" = "auth"
      }
    }
    healthCheck = {
      command     = ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
      interval    = 30
      timeout     = 5
      retries     = 3
      startPeriod = 60
    }
  }])
}

resource "aws_ecs_service" "auth" {
  name            = "${local.project}-auth"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.auth.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets         = aws_subnet.private[*].id
    security_groups = [aws_security_group.ecs.id]
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.auth.arn
    container_name   = "auth"
    container_port   = 8000
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  lifecycle {
    ignore_changes = [task_definition]
  }
}

# ─── portfolio ─────────────────────────────────────────────────

resource "aws_ecs_task_definition" "portfolio" {
  family                   = "${local.project}-portfolio"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "1024"
  memory                   = "2048"
  execution_role_arn       = aws_iam_role.task_exec.arn
  task_role_arn            = aws_iam_role.task.arn

  container_definitions = jsonencode([{
    name      = "portfolio"
    image     = "${aws_ecr_repository.services["portfolio"].repository_url}:latest"
    essential = true
    portMappings = [{ containerPort = 8001 }]
    environment = [
      { name = "ENVIRONMENT",   value = "production" },
      { name = "DATABASE_URL",  value = local.portfolio_db_url },
      { name = "TIMESCALE_URL", value = local.timescale_url },
      { name = "REDIS_URL",     value = local.redis_url },
    ]
    secrets = [
      { name = "JWT_SECRET_KEY", valueFrom = aws_secretsmanager_secret.jwt.arn }
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.ecs.name
        "awslogs-region"        = local.region
        "awslogs-stream-prefix" = "portfolio"
      }
    }
    healthCheck = {
      command     = ["CMD-SHELL", "curl -f http://localhost:8001/health || exit 1"]
      interval    = 30
      timeout     = 5
      retries     = 3
      startPeriod = 60
    }
  }])
}

resource "aws_ecs_service" "portfolio" {
  name            = "${local.project}-portfolio"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.portfolio.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets         = aws_subnet.private[*].id
    security_groups = [aws_security_group.ecs.id]
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.portfolio.arn
    container_name   = "portfolio"
    container_port   = 8001
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  lifecycle {
    ignore_changes = [task_definition]
  }
}

# ─── ai-advisor ────────────────────────────────────────────────

resource "aws_ecs_task_definition" "ai_advisor" {
  family                   = "${local.project}-ai-advisor"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "1024"
  memory                   = "2048"
  execution_role_arn       = aws_iam_role.task_exec.arn
  task_role_arn            = aws_iam_role.task.arn

  container_definitions = jsonencode([{
    name      = "ai-advisor"
    image     = "${aws_ecr_repository.services["ai-advisor"].repository_url}:latest"
    essential = true
    portMappings = [{ containerPort = 8003 }]
    environment = [
      { name = "ENVIRONMENT",           value = "production" },
      { name = "REDIS_URL",             value = local.redis_url },
      { name = "PORTFOLIO_SERVICE_URL", value = "http://portfolio.${local.project}.internal:8001" },
      { name = "AUTH_SERVICE_URL",      value = "http://auth.${local.project}.internal:8000" },
    ]
    secrets = [
      { name = "JWT_SECRET_KEY",    valueFrom = aws_secretsmanager_secret.jwt.arn },
      { name = "ANTHROPIC_API_KEY", valueFrom = aws_secretsmanager_secret.anthropic.arn },
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.ecs.name
        "awslogs-region"        = local.region
        "awslogs-stream-prefix" = "ai-advisor"
      }
    }
    healthCheck = {
      command     = ["CMD-SHELL", "curl -f http://localhost:8003/health || exit 1"]
      interval    = 30
      timeout     = 5
      retries     = 3
      startPeriod = 60
    }
  }])
}

resource "aws_ecs_service" "ai_advisor" {
  name            = "${local.project}-ai-advisor"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.ai_advisor.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets         = aws_subnet.private[*].id
    security_groups = [aws_security_group.ecs.id]
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.ai_advisor.arn
    container_name   = "ai-advisor"
    container_port   = 8003
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  lifecycle {
    ignore_changes = [task_definition]
  }
}

# ─── market-data ───────────────────────────────────────────────

resource "aws_ecs_task_definition" "market_data" {
  family                   = "${local.project}-market-data"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "512"
  memory                   = "1024"
  execution_role_arn       = aws_iam_role.task_exec.arn
  task_role_arn            = aws_iam_role.task.arn

  container_definitions = jsonencode([{
    name      = "market-data"
    image     = "${aws_ecr_repository.services["market-data"].repository_url}:latest"
    essential = true
    portMappings = [{ containerPort = 8002 }]
    environment = [
      { name = "ENVIRONMENT",           value = "production" },
      { name = "TIMESCALE_URL",         value = local.timescale_url },
      { name = "REDIS_URL",             value = local.redis_url },
      { name = "CELERY_BROKER_URL",     value = local.redis_url },
      { name = "CELERY_RESULT_BACKEND", value = local.redis_url },
    ]
    secrets = [
      { name = "ALPHA_VANTAGE_API_KEY", valueFrom = aws_secretsmanager_secret.alpha_vantage.arn }
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.ecs.name
        "awslogs-region"        = local.region
        "awslogs-stream-prefix" = "market-data"
      }
    }
    healthCheck = {
      command     = ["CMD-SHELL", "curl -f http://localhost:8002/health || exit 1"]
      interval    = 30
      timeout     = 5
      retries     = 3
      startPeriod = 60
    }
  }])
}

resource "aws_ecs_service" "market_data" {
  name            = "${local.project}-market-data"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.market_data.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets         = aws_subnet.private[*].id
    security_groups = [aws_security_group.ecs.id]
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.market.arn
    container_name   = "market-data"
    container_port   = 8002
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  lifecycle {
    ignore_changes = [task_definition]
  }
}
