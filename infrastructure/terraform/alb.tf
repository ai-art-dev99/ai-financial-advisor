resource "aws_security_group" "alb" {
  name   = "${local.project}-alb-sg"
  vpc_id = aws_vpc.main.id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${local.project}-alb-sg" }
}

resource "aws_acm_certificate" "api" {
  domain_name               = "api.${var.domain_name}"
  subject_alternative_names = ["*.${var.domain_name}"]
  validation_method         = "DNS"

  lifecycle {
    create_before_destroy = true
  }
}

# ⚠️  این resource صبر می‌کنه تا DNS validation کامل بشه
# قبل از terraform apply باید CNAME رکوردها رو به DNS اضافه کرده باشی
resource "aws_acm_certificate_validation" "api" {
  certificate_arn = aws_acm_certificate.api.arn

  timeouts {
    create = "30m"
  }
}

resource "aws_lb" "main" {
  name                       = "${local.project}-alb"
  internal                   = false
  load_balancer_type         = "application"
  security_groups            = [aws_security_group.alb.id]
  subnets                    = aws_subnet.public[*].id
  enable_deletion_protection = true

  tags = { Name = "${local.project}-alb" }
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type = "redirect"
    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}

resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.main.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = aws_acm_certificate_validation.api.certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.auth.arn
  }
}

resource "aws_lb_target_group" "auth" {
  name        = "${local.project}-auth-tg"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    path              = "/health"
    interval          = 30
    healthy_threshold = 2
  }
}

resource "aws_lb_target_group" "portfolio" {
  name        = "${local.project}-portfolio-tg"
  port        = 8001
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    path              = "/health"
    interval          = 30
    healthy_threshold = 2
  }
}

resource "aws_lb_target_group" "ai_advisor" {
  name        = "${local.project}-ai-tg"
  port        = 8003
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    path              = "/health"
    interval          = 30
    healthy_threshold = 2
  }
}

resource "aws_lb_target_group" "market" {
  name        = "${local.project}-market-tg"
  port        = 8002
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    path              = "/health"
    interval          = 30
    healthy_threshold = 2
  }
}

resource "aws_lb_listener_rule" "auth" {
  listener_arn = aws_lb_listener.https.arn
  priority     = 10

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.auth.arn
  }

  condition {
    path_pattern {
      values = ["/api/v1/auth/*"]
    }
  }
}

resource "aws_lb_listener_rule" "portfolio" {
  listener_arn = aws_lb_listener.https.arn
  priority     = 20

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.portfolio.arn
  }

  condition {
    path_pattern {
      values = ["/api/v1/portfolio/*"]
    }
  }
}

resource "aws_lb_listener_rule" "ai" {
  listener_arn = aws_lb_listener.https.arn
  priority     = 30

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.ai_advisor.arn
  }

  condition {
    path_pattern {
      values = ["/api/v1/ai/*"]
    }
  }
}

resource "aws_lb_listener_rule" "market" {
  listener_arn = aws_lb_listener.https.arn
  priority     = 40

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.market.arn
  }

  condition {
    path_pattern {
      values = ["/api/v1/market/*"]
    }
  }
}
