# Library Management System API


**Автор:** Влас Воробьев

**Группа:** М02-406 

**Дата:** 10 мая 2026  

## 📖 Описание проекта

REST API для управления библиотекой с системой рекомендаций книг.

Система позволяет регистрировать пользователей, управлять книгами, выдавать и возвращать книги, ставить оценки и получать рекомендации.


## Технологии

FastAPI, SQLAlchemy, SQLite, JWT, Pytest

## Установка

```bash
git clone https://github.com/username/library_project.git
cd library_project
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Документация: `http://127.0.0.1:8000/docs`

## Аутентификация

При первом запуске создаётся администратор:
- Username: `admin`
- Password: `admin123`

### Регистрация

```bash
curl -X POST http://127.0.0.1:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"user","email":"user@example.com","password":"pass123"}'
```

### Вход

```bash
curl -X POST http://127.0.0.1:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

Ответ содержит `access_token`. Передавайте его в заголовке:

```http
Authorization: Bearer <token>
```

## API Endpoints

### Аутентификация

| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| POST | `/auth/register` | Регистрация |
| POST | `/auth/login` | Вход |

### Пользователи

| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| GET | `/users/me` | Профиль |
| GET | `/users/me/loans/active` | Активные выдачи |
| GET | `/users/me/loans/history` | История выдач |

### Книги

| Метод | Эндпоинт | Описание | Права |
|-------|----------|----------|-------|
| POST | `/books` | Создание | admin |
| GET | `/books` | Список | user |
| GET | `/books/{id}` | По ID | user |
| PUT | `/books/{id}` | Обновление | admin |
| DELETE | `/books/{id}` | Удаление | admin |
| GET | `/books/{id}/rating` | Рейтинг | user |

### Выдача книг

| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| POST | `/loans/borrow/{book_id}` | Взять книгу |
| POST | `/loans/return/{loan_id}` | Вернуть книгу |

### Рекомендации

| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| GET | `/recommendations/for-me` | Персональные |
| GET | `/recommendations/similar-to/{book_id}` | Похожие |
| GET | `/stats/popular-books` | Популярные |

### Администрирование

| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| GET | `/admin/users` | Все пользователи |
| GET | `/admin/loans` | Все выдачи |
| PUT | `/admin/users/{user_id}/role` | Смена роли |

## Примеры запросов

### Создание книги (admin)

```bash
curl -X POST http://127.0.0.1:8000/books \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <admin_token>" \
  -d '{"title":"Мастер и Маргарита","author":"Булгаков","genre":"Роман","year":1967,"total_copies":5}'
```

### Взятие книги

```bash
curl -X POST http://127.0.0.1:8000/loans/borrow/1 \
  -H "Authorization: Bearer <user_token>"
```

### Возврат с оценкой

```bash
curl -X POST http://127.0.0.1:8000/loans/return/1 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <user_token>" \
  -d '{"rating":5}'
```

### Получение рекомендаций

```bash
curl -X GET http://127.0.0.1:8000/recommendations/for-me \
  -H "Authorization: Bearer <user_token>"
```

## Тестирование

```bash
pytest test.py -v
```

## Структура проекта

```text
library_project/
├── app/
│   ├── main.py
│   ├── models.py
│   ├── schemas.py
│   ├── auth.py
│   ├── crud.py
│   ├── recommendation.py
│   ├── database.py
│   └── test_api.py
├── requirements.txt
└── README.md
```
