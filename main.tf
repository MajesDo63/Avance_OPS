# Dungeon Shelf Infrastructure as Code (IaC) using Terraform
# This Terraform script sets up a basic infrastructure for the Dungeon Shelf application.
# It includes a VPC, subnets, security groups, and EC2 instances for a jump server and a web server.
# The script is designed to be modular and reusable, allowing for easy adjustments and scaling.
#-----------------------------------------------------------------------------------

# -------------------------------------------------------------------
# Terraform Configuration
# -------------------------------------------------------------------

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 4.0"
    }
    random = {
      source  = "hashicorp/random"
      version = ">= 3.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

# Data source: Ubuntu AMI
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"]

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-focal-20.04-amd64-server-*"]
  }
}

# --------------------------------------------------------------
# 1. VPC and Networking Resources
# --------------------------------------------------------------

resource "aws_vpc" "dungeon_shelf_vpc" {
  cidr_block           = "10.10.0.0/20"
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name = "DungeonShelfVPC"
  }
}

resource "aws_subnet" "dungeon_shelf_public_subnet" {
  vpc_id                  = aws_vpc.dungeon_shelf_vpc.id
  cidr_block              = "10.10.0.0/24"
  availability_zone       = "us-east-1a"
  map_public_ip_on_launch = true

  tags = {
    Name = "DungeonShelfPublicSubnet"
  }
}

resource "aws_internet_gateway" "dungeon_shelf_igw" {
  vpc_id = aws_vpc.dungeon_shelf_vpc.id

  tags = {
    Name = "DungeonShelfIGW"
  }
}

resource "aws_route_table" "dungeon_shelf_route_table" {
  vpc_id = aws_vpc.dungeon_shelf_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.dungeon_shelf_igw.id
  }

  tags = {
    Name = "DungeonShelfRouteTable"
  }
}

resource "aws_route_table_association" "dungeon_shelf_route_table_association" {
  subnet_id      = aws_subnet.dungeon_shelf_public_subnet.id
  route_table_id = aws_route_table.dungeon_shelf_route_table.id
}

# ---------------------------------------------------------------
# 2. Security Groups 
# ---------------------------------------------------------------

resource "aws_security_group" "dungeon_shelf_jump_sg" {
  name        = "DungeonShelfJumpSG"
  description = "Grupo de seguridad para el servidor Linux Jump"
  vpc_id      = aws_vpc.dungeon_shelf_vpc.id

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "dungeon_shelf_web_sg" {
  name        = "DungeonShelfWebSG"
  description = "Grupo de seguridad para el servidor Linux Web"
  vpc_id      = aws_vpc.dungeon_shelf_vpc.id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port       = 22
    to_port         = 22
    protocol        = "tcp"
    security_groups = [aws_security_group.dungeon_shelf_jump_sg.id]
  }

  ingress {
    from_port   = 5000
    to_port     = 5000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "DungeonShelfWebSG"
  }
}

# ---------------------------------------------------------------
# 3. EC2 Instance for Jump Server
# ---------------------------------------------------------------

resource "aws_instance" "ds_linux_jump" {
  ami                         = data.aws_ami.ubuntu.id
  instance_type               = "t2.micro"
  subnet_id                   = aws_subnet.dungeon_shelf_public_subnet.id
  vpc_security_group_ids      = [aws_security_group.dungeon_shelf_jump_sg.id]
  key_name                    = "vockey"
  associate_public_ip_address = true

  tags = {
    Name = "DungeonShelfJumpServer"
  }
}

# ----------------------------------------------------------------
# 4. EC2 Instance for Web Server
# ----------------------------------------------------------------

resource "aws_instance" "ds_linux_web" {
  ami                         = data.aws_ami.ubuntu.id
  instance_type               = "t2.micro"
  subnet_id                   = aws_subnet.dungeon_shelf_public_subnet.id
  vpc_security_group_ids      = [aws_security_group.dungeon_shelf_web_sg.id]
  key_name                    = "vockey"
  associate_public_ip_address = true

  tags = {
    Name = "DungeonShelfWebServer"
  }
}

# ---------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------

output "ds_linux_jump_public_ip" {
  value       = aws_instance.ds_linux_jump.public_ip
  description = "Public IP of the Jump Server"
}

output "ds_linux_web_public_ip" {
  value       = aws_instance.ds_linux_web.public_ip
  description = "Public IP of the Web Server"
}
