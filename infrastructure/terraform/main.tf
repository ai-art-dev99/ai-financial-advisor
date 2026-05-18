terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
  backend "s3" {
    bucket         = "robo-advisor-tfstate"
    key            = "prod/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "robo-advisor-tflock"
  }
}

provider "aws" {
  region = var.aws_region
  default_tags {
    tags = {
      Project     = "robo-advisor"
      Environment = "prod"
      ManagedBy   = "terraform"
    }
  }
}

variable "aws_region" {
  default = "us-east-1"
}
variable "domain_name" {
  description = "e.g. yourdomain.com"
}
variable "db_password" {
  sensitive = true
}
variable "jwt_secret" {
  sensitive = true
}
variable "anthropic_api_key" {
  sensitive = true
}
variable "alpha_vantage_key" {
  sensitive = true
}

data "aws_availability_zones" "available" {
  state = "available"
}
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

locals {
  project    = "robo-advisor"
  account_id = data.aws_caller_identity.current.account_id
  region     = data.aws_region.current.name
  azs        = slice(data.aws_availability_zones.available.names, 0, 2)
}

resource "aws_secretsmanager_secret" "jwt" {
  name                    = "${local.project}/jwt-secret"
  recovery_window_in_days = 7
}
resource "aws_secretsmanager_secret_version" "jwt" {
  secret_id     = aws_secretsmanager_secret.jwt.id
  secret_string = var.jwt_secret
}

resource "aws_secretsmanager_secret" "anthropic" {
  name                    = "${local.project}/anthropic-api-key"
  recovery_window_in_days = 7
}
resource "aws_secretsmanager_secret_version" "anthropic" {
  secret_id     = aws_secretsmanager_secret.anthropic.id
  secret_string = var.anthropic_api_key
}

resource "aws_secretsmanager_secret" "alpha_vantage" {
  name                    = "${local.project}/alpha-vantage-key"
  recovery_window_in_days = 7
}
resource "aws_secretsmanager_secret_version" "alpha_vantage" {
  secret_id     = aws_secretsmanager_secret.alpha_vantage.id
  secret_string = var.alpha_vantage_key
}

output "alb_dns_name" {
  value = aws_lb.main.dns_name
}
output "cloudfront_url" {
  value = "https://${aws_cloudfront_distribution.frontend.domain_name}"
}
output "frontend_bucket_name" {
  value = aws_s3_bucket.frontend.id
}
output "cloudfront_dist_id" {
  value = aws_cloudfront_distribution.frontend.id
}
output "ecr_urls" {
  value = { for k, v in aws_ecr_repository.services : k => v.repository_url }
}
output "cert_dns_validation" {
  description = "این CNAME رکوردها رو به DNS اضافه کن تا SSL تأیید بشه"
  value       = aws_acm_certificate.api.domain_validation_options
}
