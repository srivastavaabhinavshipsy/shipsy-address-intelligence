# Frontend Dockerfile
FROM node:18-alpine

# Set working directory
WORKDIR /app

# 2GIS Map API Key for Kazakhstan support
ENV REACT_APP_2GIS_API_KEY=6d5af39c-442f-4abb-9dbd-98c2f85c0f8d

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production

# Copy application files
COPY . .

# Build the React app
RUN npm run build

# Install serve to serve the build
RUN npm install -g serve

# Expose port
EXPOSE 3000

# Serve the built app
CMD ["serve", "-s", "build", "-l", "3000"]
