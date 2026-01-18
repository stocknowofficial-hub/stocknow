# Base Image
FROM node:20-alpine

# Install libc6-compat for Next.js on Alpine
RUN apk add --no-cache libc6-compat

# Working Directory
WORKDIR /app

# Copy package.json
COPY package*.json ./

# Install Dependencies
RUN npm install

# Copy Code
COPY . .

# Build for Production
# RUN npm run build  <-- Dev mode for migration first, usually we use dev in docker-compose for immediate feedback, or build for prod.
# Let's assume Production usage on Mac, so run build.
# BUT User said "git pull" -> "reflect". So maybe `npm run start` after build.
# For simplicity in this robust guide, we'll keep it simple: 
# Using dev server in docker is easier for "git pull and see changes" without rebuild, 
# but prod is better for performance. User said "Production Server".
# Let's do a build.

RUN npm run build

# Expose Port
EXPOSE 3000

# Start Command
CMD ["npm", "start"]
