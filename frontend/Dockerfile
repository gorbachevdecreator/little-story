# ЭТАП 1: Сборка (Build)
FROM node:20-alpine as build-stage

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

# Копируем собранные файлы сайта
COPY --from=build-stage /app/dist /usr/share/nginx/html

# !!! ДОБАВЛЯЕМ ЭТУ СТРОКУ НИЖЕ !!!
# Копируем наш конфиг Nginx внутрь контейнера
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Открываем 80 порт
EXPOSE 80

# Запускаем Nginx
CMD ["nginx", "-g", "daemon off;"]