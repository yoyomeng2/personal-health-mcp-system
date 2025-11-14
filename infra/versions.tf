terraform {
  required_version = "~> 1"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 3.61.0"
    }
  }

  backend "s3" {
    bucket = "personal-health-mcp-system-terraform-state"
    key    = "infra/terraform.tfstate"
    region = "us-east-1"
  }
}
