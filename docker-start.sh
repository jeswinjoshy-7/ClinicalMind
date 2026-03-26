#!/bin/bash

# ClinicalMind Docker Startup Script
# This script builds and starts all services

set -e

echo "🏥 ClinicalMind - Docker Deployment"
echo "===================================="

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  Warning: .env file not found!"
    echo "   Copy .env.example to .env and add your GROQ_API_KEY"
    echo ""
    read -p "Do you want to continue? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Build and start services
echo "📦 Building Docker images..."
docker-compose build

echo "🚀 Starting services..."
docker-compose up -d

echo ""
echo "✅ Services started!"
echo ""
echo "📊 View logs:"
echo "   docker-compose logs -f"
echo ""
echo "🌐 Access the application:"
echo "   Frontend: http://localhost:3000"
echo "   Backend:  http://localhost:8000"
echo "   API Docs: http://localhost:8000/docs"
echo ""
echo "🛑 To stop:"
echo "   docker-compose down"
echo ""
echo "🗑️  To stop and remove volumes:"
echo "   docker-compose down -v"
