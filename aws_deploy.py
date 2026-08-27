#!/usr/bin/env python3
"""
CloudGuard AWS Lab Deployment Script
Automates Docker build, push, and ECS deployment

Usage:
    python aws_deploy.py --build-and-push --region us-east-1
    python aws_deploy.py --deploy-ecs --cluster cloudguard-cluster
    python aws_deploy.py --full --region us-east-1 --cluster cloudguard-cluster
"""

import os
import sys
import subprocess
import argparse
import json
from pathlib import Path
from datetime import datetime

class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def run_command(cmd, description=""):
    """Execute a command and handle errors"""
    if description:
        print(f"{Colors.BLUE}▸ {description}...{Colors.ENDC}")

    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"{Colors.RED}✗ Failed: {description}{Colors.ENDC}")
        print(result.stderr)
        return False

    print(f"{Colors.GREEN}✓ {description}{Colors.ENDC}")
    return True

def get_aws_account_id():
    """Get AWS account ID"""
    result = subprocess.run(
        "aws sts get-caller-identity --query Account --output text",
        shell=True,
        capture_output=True,
        text=True
    )
    return result.stdout.strip() if result.returncode == 0 else None

def build_docker_image(service, region):
    """Build Docker image for service"""
    account_id = get_aws_account_id()
    if not account_id:
        print(f"{Colors.RED}✗ Could not get AWS account ID{Colors.ENDC}")
        return False

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    image_uri = f"{account_id}.dkr.ecr.{region}.amazonaws.com/cloudguard-{service}:latest"
    image_uri_versioned = f"{image_uri}-{timestamp}"

    print(f"\n{Colors.CYAN}Building {service} Docker image...{Colors.ENDC}")

    # Build image
    cmd = f"docker build -t {image_uri} -t {image_uri_versioned} ./{service}"
    if not run_command(cmd, f"Building {service} Docker image"):
        return False

    return (image_uri, image_uri_versioned)

def push_docker_image(image_uri, region):
    """Push Docker image to ECR"""
    account_id = get_aws_account_id()

    print(f"\n{Colors.CYAN}Pushing image to ECR...{Colors.ENDC}")

    # Login to ECR
    cmd = f"aws ecr get-login-password --region {region} | docker login --username AWS --password-stdin {account_id}.dkr.ecr.{region}.amazonaws.com"
    if not run_command(cmd, "Logging in to ECR"):
        return False

    # Create repository if it doesn't exist
    repo_name = image_uri.split("/")[1].split(":")[0]
    cmd = f"aws ecr describe-repositories --repository-names {repo_name} --region {region} 2>/dev/null || aws ecr create-repository --repository-name {repo_name} --region {region}"
    run_command(cmd, f"Creating ECR repository {repo_name}")

    # Push image
    cmd = f"docker push {image_uri}"
    if not run_command(cmd, f"Pushing {image_uri} to ECR"):
        return False

    return image_uri

def update_ecs_service(service, image_uri, cluster, region):
    """Update ECS service with new image"""
    print(f"\n{Colors.CYAN}Updating ECS service...{Colors.ENDC}")

    # Get current task definition
    cmd = f"aws ecs describe-services --cluster {cluster} --services cloudguard-{service} --region {region} --query 'services[0].taskDefinition' --output text"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    task_def_arn = result.stdout.strip()

    if not task_def_arn:
        print(f"{Colors.RED}✗ Could not find task definition{Colors.ENDC}")
        return False

    # Get task definition JSON
    cmd = f"aws ecs describe-task-definition --task-definition {task_def_arn} --region {region} --query 'taskDefinition' --output json > /tmp/task-def.json"
    if not run_command(cmd, "Fetching current task definition"):
        return False

    # Update image in task definition
    with open("/tmp/task-def.json", "r") as f:
        task_def = json.load(f)

    # Remove fields that can't be updated
    for key in ["taskDefinitionArn", "revision", "status", "requiresAttributes", "compatibilities", "registeredAt", "registeredBy"]:
        task_def.pop(key, None)

    # Update container image
    for container in task_def.get("containerDefinitions", []):
        if container["name"] == service:
            container["image"] = image_uri

    # Register new task definition
    cmd = f"aws ecs register-task-definition --cli-input-json file:///tmp/task-def.json --region {region} --query 'taskDefinition.taskDefinitionArn' --output text"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    new_task_def_arn = result.stdout.strip()

    if not new_task_def_arn:
        print(f"{Colors.RED}✗ Could not register new task definition{Colors.ENDC}")
        return False

    print(f"{Colors.GREEN}✓ Registered new task definition: {new_task_def_arn}{Colors.ENDC}")

    # Update service
    cmd = f"aws ecs update-service --cluster {cluster} --service cloudguard-{service} --task-definition {new_task_def_arn} --region {region}"
    if not run_command(cmd, f"Updating ECS service cloudguard-{service}"):
        return False

    return True

def print_banner():
    """Print deployment banner"""
    print(f"""
{Colors.BOLD}{Colors.CYAN}
╔════════════════════════════════════════════════════════════════════════════╗
║                                                                            ║
║              🚀 CloudGuard AWS Lab Deployment                             ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝
{Colors.ENDC}
""")

def main():
    parser = argparse.ArgumentParser(description="CloudGuard AWS Lab Deployment")
    parser.add_argument("--build-backend", action="store_true", help="Build backend Docker image")
    parser.add_argument("--build-frontend", action="store_true", help="Build frontend Docker image")
    parser.add_argument("--build-all", action="store_true", help="Build both images")
    parser.add_argument("--push", action="store_true", help="Push images to ECR")
    parser.add_argument("--deploy-ecs", action="store_true", help="Deploy to ECS")
    parser.add_argument("--full", action="store_true", help="Build, push, and deploy")
    parser.add_argument("--region", default="us-east-1", help="AWS region")
    parser.add_argument("--cluster", default="cloudguard-cluster", help="ECS cluster name")

    args = parser.parse_args()

    print_banner()

    # Verify AWS credentials
    if not get_aws_account_id():
        print(f"{Colors.RED}✗ AWS credentials not configured{Colors.ENDC}")
        sys.exit(1)

    # Build
    if args.full or args.build_all or args.build_backend or args.build_frontend:
        services = []
        if args.build_all or args.full:
            services = ["backend", "frontend"]
        else:
            if args.build_backend:
                services.append("backend")
            if args.build_frontend:
                services.append("frontend")

        for service in services:
            result = build_docker_image(service, args.region)
            if not result:
                sys.exit(1)

    # Push
    if args.full or args.push:
        for service in ["backend", "frontend"]:
            result = build_docker_image(service, args.region)
            if not result:
                continue

            image_uri, _ = result
            pushed_uri = push_docker_image(image_uri, args.region)

            if args.deploy_ecs or args.full:
                update_ecs_service(service, pushed_uri, args.cluster, args.region)

    print(f"\n{Colors.BOLD}{Colors.GREEN}✅ Deployment complete!{Colors.ENDC}\n")
    print(f"Cluster: {Colors.BOLD}{args.cluster}{Colors.ENDC}")
    print(f"Region: {Colors.BOLD}{args.region}{Colors.ENDC}")
    print(f"\nView deployment status:")
    print(f"  aws ecs describe-services --cluster {args.cluster} --services cloudguard-backend cloudguard-frontend --region {args.region}\n")

if __name__ == "__main__":
    main()
