resource "aws_db_subnet_group" "main" {
  name       = "${local.project}-db-subnet"
  subnet_ids = aws_subnet.private[*].id
}

resource "aws_security_group" "rds" {
  name   = "${local.project}-rds-sg"
  vpc_id = aws_vpc.main.id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs.id]
  }

  tags = { Name = "${local.project}-rds-sg" }
}

resource "aws_db_instance" "main" {
  identifier            = "${local.project}-postgres"
  engine                = "postgres"
  engine_version        = "16"
  instance_class        = "db.t3.micro"
  allocated_storage     = 20
  max_allocated_storage = 100
  storage_encrypted     = true

  db_name  = "robo_auth"
  username = "robo_user"
  password = var.db_password

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  backup_retention_period   = 0
  deletion_protection       = true
  skip_final_snapshot       = false
  final_snapshot_identifier = "${local.project}-final-snapshot"

  tags = { Name = "${local.project}-postgres" }
}

resource "aws_db_instance" "timescale" {
  identifier            = "${local.project}-timescale"
  engine                = "postgres"
  engine_version        = "16"
  instance_class        = "db.t3.micro"
  allocated_storage     = 30
  max_allocated_storage = 200
  storage_encrypted     = true

  db_name  = "robo_market"
  username = "robo_user"
  password = var.db_password

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  backup_retention_period   = 0
  deletion_protection       = true
  skip_final_snapshot       = false
  final_snapshot_identifier = "${local.project}-timescale-snapshot"

  tags = { Name = "${local.project}-timescale" }
}

locals {
  auth_db_url      = "postgresql+asyncpg://robo_user:${var.db_password}@${aws_db_instance.main.address}:5432/robo_auth"
  portfolio_db_url = "postgresql+asyncpg://robo_user:${var.db_password}@${aws_db_instance.main.address}:5432/robo_portfolio"
  timescale_url    = "postgresql+asyncpg://robo_user:${var.db_password}@${aws_db_instance.timescale.address}:5432/robo_market"
}
