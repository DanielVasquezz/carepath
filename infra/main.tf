# 1. Terraform Settings & Provider
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

# 2. Network (VPC)
resource "aws_vpc" "carepath_vpc" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
  tags = { Name = "CarePath-VPC" }
}

# 3. Public Subnet
resource "aws_subnet" "carepath_public_subnet" {
  vpc_id                  = aws_vpc.carepath_vpc.id
  cidr_block              = "10.0.1.0/24"
  map_public_ip_on_launch = true
  availability_zone       = "us-east-1a"
  tags = { Name = "CarePath-Public-Subnet" }
}

# 4. Internet Connection (IGW & Route Table)
resource "aws_internet_gateway" "carepath_igw" {
  vpc_id = aws_vpc.carepath_vpc.id
}

resource "aws_route_table" "carepath_public_rt" {
  vpc_id = aws_vpc.carepath_vpc.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.carepath_igw.id
  }
}

resource "aws_route_table_association" "carepath_public_assoc" {
  subnet_id      = aws_subnet.carepath_public_subnet.id
  route_table_id = aws_route_table.carepath_public_rt.id
}

# 5. Security Group (Firewall)
resource "aws_security_group" "carepath_api_sg" {
  name   = "carepath-api-sg"
  vpc_id = aws_vpc.carepath_vpc.id

  ingress {
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

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

# 6. The Server (EC2)
resource "aws_instance" "carepath_server" {
  ami                    = "ami-0c7217cdde317cfec" # Amazon Linux 2023
  instance_type          = "t3.micro"
  subnet_id              = aws_subnet.carepath_public_subnet.id
  vpc_security_group_ids = [aws_security_group.carepath_api_sg.id]

  user_data = <<-EOF
              #!/bin/bash
              dnf update -y
              dnf install -y docker
              systemctl start docker
              systemctl enable docker
              EOF

  tags = { Name = "CarePath-Server" }
}

# 7. Output the IP
output "server_public_ip" {
  value = aws_instance.carepath_server.public_ip
}