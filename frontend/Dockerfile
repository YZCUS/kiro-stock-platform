FROM node:18-alpine

WORKDIR /app

# 複製 package 檔案
COPY package*.json ./

# 安裝依賴
RUN npm ci --only=production

# 複製應用程式碼
COPY . .

# 建置應用程式
RUN npm run build

# 暴露端口
EXPOSE 3000

# 啟動命令
CMD ["npm", "start"]