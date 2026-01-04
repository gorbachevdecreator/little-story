# ЭТАП 1: Сборка (Build)
FROM node:18-alpine as build-stage

# Рабочая папка
WORKDIR /app

# Копируем файлы package.json и устанавливаем зависимости
COPY package*.json ./
RUN npm install

# Копируем исходный код и собираем проект (создается папка dist)
COPY . .
RUN npm run build

# ЭТАП 2: Запуск (Production)
FROM nginx:stable-alpine as production-stage

# Копируем собранные файлы из этапа 1 в папку Nginx
COPY --from=build-stage /app/dist /usr/share/nginx/html

# Открываем 80 порт
EXPOSE 80

# Запускаем Nginx
CMD ["nginx", "-g", "daemon off;"]