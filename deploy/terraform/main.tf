# Universal Agent Economy OS - Terraform Foundation
# 
# This configuration provides a one-command deployment skeleton for enterprise acquirers.
# It is designed to seamlessly deploy the containerized application defined in our Dockerfile,
# mirroring the simplicity of our existing railway.toml but for AWS/GCP/Azure/Railway environments.
# 
# Strategic Value: Demonstrates immediate enterprise readiness, scalability, and 
# infrastructure-as-code best practices for the entire agent-economy-os asset.

terraform {
  required_version = ">= 1.0.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    # Supabase Provider for Identity Engine & Schema Management
    # supabase = {
    #   source = "supabase/supabase"
    #   version = "~> 1.0"
    # }
    # Railway Provider for PaaS Deployment (aligns with railway.toml)
    # railway = {
    #   source = "terraform-community-providers/railway"
    #   version = "~> 0.3"
    # }
  }
}

provider "aws" {
  region = var.aws_region
}

# ==========================================
# 1. Core Infrastructure (VPC, Networking)
# ==========================================
# Placeholder: Define VPC, Subnets, Internet Gateway, Security Groups, etc.
# resource "aws_vpc" "main" { ... }

# ==========================================
# 2. Database & Identity (Supabase Schema)
# ==========================================
# The Identity Engine relies on Supabase for agent registration and credential storage.
# This section provisions the project and applies the core schema.
# 
# resource "supabase_project" "uaeos_db" {
#   organization_id   = var.supabase_org_id
#   name              = "${var.app_name}-${var.environment}-db"
#   database_password = var.supabase_db_password
#   region            = var.aws_region
# }
#
# resource "supabase_settings" "uaeos_settings" {
#   project_ref = supabase_project.uaeos_db.id
#   api         = true
# }
#
# # Apply the core schema for the Identity Engine
# resource "supabase_sql" "core_schema" {
#   project_ref = supabase_project.uaeos_db.id
#   sql         = file("../../supabase/migrations/20231001_initial_schema.sql")
# }

# ==========================================
# 3. Caching & Rate Limiting (Redis)
# ==========================================
# The proxy uses Redis for rate limiting, caching, and analytics (app/cache.py, app/rate_limit.py).
# This replaces the in-memory fallback for production horizontal scaling.
# 
# resource "aws_elasticache_cluster" "uaeos_redis" {
#   cluster_id           = "${var.app_name}-${var.environment}-redis"
#   engine               = "redis"
#   node_type            = "cache.t3.micro"
#   num_cache_nodes      = 1
#   parameter_group_name = "default.redis7"
#   engine_version       = "7.0"
#   port                 = 6379
# }

# ==========================================
# 4. Railway-Specific Config (PaaS Alternative)
# ==========================================
# For teams preferring PaaS over raw AWS ECS, this mirrors our railway.toml.
# It deploys the Dockerfile and sets the required environment variables.
#
# resource "railway_project" "uaeos_project" {
#   name = "${var.app_name}-${var.environment}"
# }
#
# resource "railway_environment" "production" {
#   project_id = railway_project.uaeos_project.id
#   name       = "production"
# }
#
# resource "railway_service" "fastapi_core" {
#   project_id     = railway_project.uaeos_project.id
#   name           = "uaeos-proxy"
#   source_repo    = "agentrails/agent-economy-os"
#   builder        = "DOCKERFILE"
#   dockerfile_path= "Dockerfile"
#   start_command  = "sh -c 'uvicorn app.main:app --host 0.0.0.0 --port $${PORT:-8000}'"
# }
#
# resource "railway_variable" "env_vars" {
#   for_each = {
#     ENVIRONMENT           = var.environment
#     API_KEY               = var.api_key
#     STRIPE_SECRET_KEY     = var.stripe_secret_key
#     STRIPE_WEBHOOK_SECRET = var.stripe_webhook_secret
#     SUPABASE_URL          = supabase_project.uaeos_db.api_url
#     SUPABASE_KEY          = supabase_project.uaeos_db.service_role_key
#     REDIS_URL             = "redis://${aws_elasticache_cluster.uaeos_redis.cache_nodes[0].address}:6379"
#   }
#   project_id     = railway_project.uaeos_project.id
#   environment_id = railway_environment.production.id
#   service_id     = railway_service.fastapi_core.id
#   name           = each.key
#   value          = each.value
# }

# ==========================================
# 5. Application Service (AWS ECS Container Deployment)
# ==========================================
# This service runs the FastAPI proxy on AWS ECS Fargate. It builds from the root Dockerfile.
# It requires environment variables defined in app/config.py (API_KEY, STRIPE_SECRET_KEY, etc.).
#
# resource "aws_ecs_cluster" "uaeos_cluster" {
#   name = "${var.app_name}-${var.environment}-cluster"
# }
#
# resource "aws_ecs_task_definition" "uaeos_task" {
#   family                   = "${var.app_name}-${var.environment}-task"
#   network_mode             = "awsvpc"
#   requires_compatibilities = ["FARGATE"]
#   cpu                      = "256"
#   memory                   = "512"
#   execution_role_arn       = aws_iam_role.ecs_execution_role.arn
#
#   container_definitions = jsonencode([
#     {
#       name      = "${var.app_name}"
#       image     = var.docker_image
#       essential = true
#       portMappings = [
#         {
#           containerPort = var.container_port
#           hostPort      = var.container_port
#           protocol      = "tcp"
#         }
#       ]
#       environment = [
#         { name = "ENVIRONMENT", value = var.environment },
#         { name = "API_KEY", value = var.api_key },
#         { name = "STRIPE_SECRET_KEY", value = var.stripe_secret_key },
#         { name = "STRIPE_WEBHOOK_SECRET", value = var.stripe_webhook_secret },
#         { name = "SUPABASE_URL", value = var.supabase_url },
#         { name = "SUPABASE_KEY", value = var.supabase_key },
#         { name = "REDIS_URL", value = var.redis_url }
#       ]
#       logConfiguration = {
#         logDriver = "awslogs"
#         options = {
#           "awslogs-group"         = "/ecs/${var.app_name}-${var.environment}"
#           "awslogs-region"        = var.aws_region
#           "awslogs-stream-prefix" = "ecs"
#         }
#       }
#     }
#   ])
# }
#
# resource "aws_ecs_service" "uaeos_service" {
#   name            = "${var.app_name}-${var.environment}-service"
#   cluster         = aws_ecs_cluster.uaeos_cluster.id
#   task_definition = aws_ecs_task_definition.uaeos_task.arn
#   desired_count   = 2
#   launch_type     = "FARGATE"
#
#   network_configuration {
#     subnets         = aws_subnet.private[*].id
#     security_groups = [aws_security_group.ecs_tasks.id]
#   }
#
#   load_balancer {
#     target_group_arn = aws_lb_target_group.uaeos_tg.arn
#     container_name   = var.app_name
#     container_port   = var.container_port
#   }
# }

# ==========================================
# 6. Load Balancing & Security Groups
# ==========================================
# Exposes the proxy to the internet securely, routing traffic to the ECS tasks.

# resource "aws_security_group" "alb_sg" {
#   name        = "${var.app_name}-${var.environment}-alb-sg"
#   description = "Allow inbound HTTP/HTTPS traffic"
#   vpc_id      = aws_vpc.main.id
#
#   ingress {
#     from_port   = 80
#     to_port     = 80
#     protocol    = "tcp"
#     cidr_blocks = ["0.0.0.0/0"]
#   }
#   
#   ingress {
#     from_port   = 443
#     to_port     = 443
#     protocol    = "tcp"
#     cidr_blocks = ["0.0.0.0/0"]
#   }
#
#   egress {
#     from_port   = 0
#     to_port     = 0
#     protocol    = "-1"
#     cidr_blocks = ["0.0.0.0/0"]
#   }
# }

# resource "aws_security_group" "ecs_tasks" {
#   name        = "${var.app_name}-${var.environment}-ecs-tasks-sg"
#   description = "Allow inbound traffic from ALB only"
#   vpc_id      = aws_vpc.main.id
#
#   ingress {
#     from_port       = var.container_port
#     to_port         = var.container_port
#     protocol        = "tcp"
#     security_groups = [aws_security_group.alb_sg.id]
#   }
#
#   egress {
#     from_port   = 0
#     to_port     = 0
#     protocol    = "-1"
#     cidr_blocks = ["0.0.0.0/0"]
#   }
# }

# resource "aws_lb" "uaeos_alb" {
#   name               = "${var.app_name}-${var.environment}-alb"
#   internal           = false
#   load_balancer_type = "application"
#   security_groups    = [aws_security_group.alb_sg.id]
#   subnets            = aws_subnet.public[*].id
# }

# resource "aws_lb_target_group" "uaeos_tg" {
#   name        = "${var.app_name}-${var.environment}-tg"
#   port        = var.container_port
#   protocol    = "HTTP"
#   vpc_id      = aws_vpc.main.id
#   target_type = "ip"
#
#   health_check {
#     path                = "/health"
#     healthy_threshold   = 3
#     unhealthy_threshold = 3
#     timeout             = 5
#     interval            = 30
#     matcher             = "200"
#   }
# }

# resource "aws_lb_listener" "http" {
#   load_balancer_arn = aws_lb.uaeos_alb.arn
#   port              = "80"
#   protocol          = "HTTP"
#
#   default_action {
#     type             = "forward"
#     target_group_arn = aws_lb_target_group.uaeos_tg.arn
#   }
# }