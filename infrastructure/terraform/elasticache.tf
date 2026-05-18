resource "aws_elasticache_subnet_group" "main" {
  name       = "${local.project}-redis-subnet"
  subnet_ids = aws_subnet.private[*].id
}

resource "aws_security_group" "redis" {
  name   = "${local.project}-redis-sg"
  vpc_id = aws_vpc.main.id

  ingress {
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs.id]
  }

  tags = { Name = "${local.project}-redis-sg" }
}

resource "aws_elasticache_replication_group" "main" {
  replication_group_id = "${local.project}-redis"
  description          = "Redis for ${local.project}"
  node_type            = "cache.t3.small"
  num_cache_clusters   = 1
  port                 = 6379

  subnet_group_name  = aws_elasticache_subnet_group.main.name
  security_group_ids = [aws_security_group.redis.id]

  at_rest_encryption_enabled = true
  automatic_failover_enabled = false

  tags = { Name = "${local.project}-redis" }
}

locals {
  redis_url = "redis://${aws_elasticache_replication_group.main.primary_endpoint_address}:6379"
}
