# Build stage
FROM node:18-alpine AS builder

WORKDIR /app

# 複製 package 檔案
COPY package*.json ./

# 安裝所有依賴（包括開發依賴，用於構建）
RUN npm ci

# 複製應用程式碼
COPY . .

# 建置應用程式
RUN npm run build

# Production stage
FROM node:18-alpine AS runner

WORKDIR /app

# 複製 package 檔案
COPY package*.json ./

# 僅安裝生產依賴
RUN npm ci --only=production && npm cache clean --force

# 複製構建結果
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public

# 暴露端口
EXPOSE 3000

# 啟動命令
CMD ["npm", "start"]