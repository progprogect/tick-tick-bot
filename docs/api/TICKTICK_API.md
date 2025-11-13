# TickTick Open API Documentation

**Версия:** 1.0  
**Дата:** 2024-11-04  
**Источник:** [TickTick Developer Center](https://developer.ticktick.com/)

---

## Содержание

1. [Введение](#введение)
2. [Авторизация](#авторизация)
3. [API Reference](#api-reference)
   - [Task (Задачи)](#task-задачи)
   - [Project (Проекты/Списки)](#project-проектысписки)
4. [Модели данных](#модели-данных)
5. [Важные замечания](#важные-замечания)

---

## Введение

TickTick Open API позволяет разработчикам интегрировать функции управления задачами TickTick в свои приложения.

### Начало работы

Для использования TickTick Open API необходимо:
1. Зарегистрировать приложение в [TickTick Developer Center](https://developer.ticktick.com/)
2. Получить `client_id` и `client_secret`
3. Использовать OAuth2 для получения `access_token`

---

## Авторизация

### Получение Access Token

TickTick использует протокол OAuth2 для получения access token.

#### Шаг 1: Перенаправление пользователя

Перенаправьте пользователя на страницу авторизации TickTick:

```
https://ticktick.com/oauth/authorize?scope={scope}&client_id={client_id}&state={state}&redirect_uri={redirect_uri}&response_type=code
```

**Параметры:**

| Параметр | Описание |
|----------|----------|
| `client_id` | Уникальный ID приложения |
| `scope` | Разрешения через пробел. Доступные: `tasks:write`, `tasks:read` |
| `state` | Передается в redirect_uri как есть |
| `redirect_uri` | URL перенаправления, настроенный пользователем |
| `response_type` | Фиксированное значение: `code` |

#### Шаг 2: Получение authorization code

После предоставления доступа TickTick перенаправит пользователя обратно на `redirect_uri` с параметрами:

| Параметр | Описание |
|----------|----------|
| `code` | Authorization code для получения access token |
| `state` | Параметр state из первого шага |

#### Шаг 3: Обмен code на access token

Отправьте POST запрос на `https://ticktick.com/oauth/token`:

**Content-Type:** `application/x-www-form-urlencoded`

**Параметры:**

| Параметр | Описание | Расположение |
|----------|----------|--------------|
| `client_id` | Username в HEADER через Basic Auth | Header |
| `client_secret` | Password в HEADER через Basic Auth | Header |
| `code` | Code, полученный на шаге 2 | Body |
| `grant_type` | Тип grant, сейчас только `authorization_code` | Body |
| `scope` | Разрешения через пробел: `tasks:write`, `tasks:read` | Body |
| `redirect_uri` | URL перенаправления, настроенный пользователем | Body |

**Ответ:**

```json
{
  "access_token": "access token value",
  ...
}
```

### Использование Access Token

Установите заголовок `Authorization` в запросах:

```
Authorization: Bearer {access_token}
```

**Пример:**

```
Authorization: Bearer e*****b
```

---

## API Reference

### Base URL

```
https://api.ticktick.com
```

### API Version

```
/open/v1
```

---

## Task (Задачи)

### 1. Получить задачу по Project ID и Task ID

**GET** `/open/v1/project/{projectId}/task/{taskId}`

**Параметры:**

| Тип | Имя | Описание | Обязательный |
|-----|-----|----------|--------------|
| Path | `projectId` | ID проекта | ✅ |
| Path | `taskId` | ID задачи | ✅ |

**Ответы:**

| HTTP Code | Описание | Schema |
|-----------|----------|--------|
| 200 | OK | Task |
| 401 | Unauthorized | - |
| 403 | Forbidden | - |
| 404 | Not Found | - |

**Пример запроса:**

```http
GET /open/v1/project/{{projectId}}/task/{{taskId}} HTTP/1.1
Host: api.ticktick.com
Authorization: Bearer {{token}}
```

**Пример ответа:**

```json
{
  "id": "63b7bebb91c0a5474805fcd4",
  "isAllDay": true,
  "projectId": "6226ff9877acee87727f6bca",
  "title": "Task Title",
  "content": "Task Content",
  "desc": "Task Description",
  "timeZone": "America/Los_Angeles",
  "repeatFlag": "RRULE:FREQ=DAILY;INTERVAL=1",
  "startDate": "2019-11-13T03:00:00+0000",
  "dueDate": "2019-11-14T03:00:00+0000",
  "reminders": ["TRIGGER:P0DT9H0M0S", "TRIGGER:PT0S"],
  "priority": 1,
  "status": 0,
  "completedTime": "2019-11-13T03:00:00+0000",
  "sortOrder": 12345,
  "items": [{
    "id": "6435074647fd2e6387145f20",
    "status": 0,
    "title": "Item Title",
    "sortOrder": 12345,
    "startDate": "2019-11-13T03:00:00+0000",
    "isAllDay": false,
    "timeZone": "America/Los_Angeles",
    "completedTime": "2019-11-13T03:00:00+0000"
  }]
}
```

---

### 2. Создать задачу

**POST** `/open/v1/task`

**Параметры (Body):**

| Параметр | Тип | Описание | Обязательный | Формат |
|----------|-----|----------|--------------|--------|
| `title` | string | Название задачи | ✅ | - |
| `projectId` | string | ID проекта | ✅ | - |
| `content` | string | Содержимое задачи | ❌ | - |
| `desc` | string | Описание чеклиста | ❌ | - |
| `isAllDay` | boolean | Весь день | ❌ | - |
| `startDate` | date | Дата начала | ❌ | `yyyy-MM-dd'T'HH:mm:ssZ` |
| `dueDate` | date | Дата выполнения | ❌ | `yyyy-MM-dd'T'HH:mm:ssZ` |
| `timeZone` | string | Часовой пояс | ❌ | - |
| `reminders` | list | Список напоминаний | ❌ | - |
| `repeatFlag` | string | Правила повторения | ❌ | RRULE формат |
| `priority` | integer | Приоритет задачи | ❌ | 0 (по умолчанию) |
| `sortOrder` | integer | Порядок сортировки | ❌ | - |
| `items` | list | Список подзадач | ❌ | - |

**Формат даты:**

```
yyyy-MM-dd'T'HH:mm:ssZ
Пример: "2019-11-13T03:00:00+0000"
```

**Ответы:**

| HTTP Code | Описание | Schema |
|-----------|----------|--------|
| 200 | OK | Task |
| 201 | Created | - |
| 401 | Unauthorized | - |
| 403 | Forbidden | - |
| 404 | Not Found | - |

**Пример запроса:**

```http
POST /open/v1/task HTTP/1.1
Host: api.ticktick.com
Content-Type: application/json
Authorization: Bearer {{token}}

{
  "title": "Task Title",
  "projectId": "6226ff9877acee87727f6bca"
}
```

**Пример ответа:**

```json
{
  "id": "63b7bebb91c0a5474805fcd4",
  "projectId": "6226ff9877acee87727f6bca",
  "title": "Task Title",
  "content": "Task Content",
  "desc": "Task Description",
  "isAllDay": true,
  "startDate": "2019-11-13T03:00:00+0000",
  "dueDate": "2019-11-14T03:00:00+0000",
  "timeZone": "America/Los_Angeles",
  "reminders": ["TRIGGER:P0DT9H0M0S", "TRIGGER:PT0S"],
  "repeatFlag": "RRULE:FREQ=DAILY;INTERVAL=1",
  "priority": 1,
  "status": 0,
  "completedTime": "2019-11-13T03:00:00+0000",
  "sortOrder": 12345,
  "items": [{
    "id": "6435074647fd2e6387145f20",
    "status": 1,
    "title": "Subtask Title",
    "sortOrder": 12345,
    "startDate": "2019-11-13T03:00:00+0000",
    "isAllDay": false,
    "timeZone": "America/Los_Angeles",
    "completedTime": "2019-11-13T03:00:00+0000"
  }]
}
```

---

### 3. Обновить задачу

**POST** `/open/v1/task/{taskId}`

**Параметры:**

| Тип | Имя | Описание | Обязательный |
|-----|-----|----------|--------------|
| Path | `taskId` | ID задачи | ✅ |
| Body | `id` | ID задачи | ✅ |
| Body | `projectId` | ID проекта | ✅ |
| Body | `title` | Название задачи | ❌ |
| Body | `content` | Содержимое задачи | ❌ |
| Body | `desc` | Описание чеклиста | ❌ |
| Body | `isAllDay` | Весь день | ❌ |
| Body | `startDate` | Дата начала | ❌ |
| Body | `dueDate` | Дата выполнения | ❌ |
| Body | `timeZone` | Часовой пояс | ❌ |
| Body | `reminders` | Список напоминаний | ❌ |
| Body | `repeatFlag` | Правила повторения | ❌ |
| Body | `priority` | Приоритет задачи | ❌ |
| Body | `sortOrder` | Порядок сортировки | ❌ |
| Body | `items` | Список подзадач | ❌ |

**Важно:** При обновлении задачи **ОБЯЗАТЕЛЬНО** нужно передавать `id` и `projectId` в теле запроса!

**Ответы:**

| HTTP Code | Описание | Schema |
|-----------|----------|--------|
| 200 | OK | Task |
| 201 | Created | - |
| 401 | Unauthorized | - |
| 403 | Forbidden | - |
| 404 | Not Found | - |

**Пример запроса:**

```http
POST /open/v1/task/{{taskId}} HTTP/1.1
Host: api.ticktick.com
Content-Type: application/json
Authorization: Bearer {{token}}

{
  "id": "{{taskId}}",
  "projectId": "{{projectId}}",
  "title": "Task Title",
  "priority": 1
}
```

**Пример ответа:**

```json
{
  "id": "63b7bebb91c0a5474805fcd4",
  "projectId": "6226ff9877acee87727f6bca",
  "title": "Task Title",
  "content": "Task Content",
  "desc": "Task Description",
  "isAllDay": true,
  "startDate": "2019-11-13T03:00:00+0000",
  "dueDate": "2019-11-14T03:00:00+0000",
  "timeZone": "America/Los_Angeles",
  "reminders": ["TRIGGER:P0DT9H0M0S", "TRIGGER:PT0S"],
  "repeatFlag": "RRULE:FREQ=DAILY;INTERVAL=1",
  "priority": 1,
  "status": 0,
  "completedTime": "2019-11-13T03:00:00+0000",
  "sortOrder": 12345,
  "items": [{
    "id": "6435074647fd2e6387145f20",
    "status": 1,
    "title": "Item Title",
    "sortOrder": 12345,
    "startDate": "2019-11-13T03:00:00+0000",
    "isAllDay": false,
    "timeZone": "America/Los_Angeles",
    "completedTime": "2019-11-13T03:00:00+0000"
  }],
  "kind": "CHECKLIST"
}
```

---

### 4. Завершить задачу

**POST** `/open/v1/project/{projectId}/task/{taskId}/complete`

**Параметры:**

| Тип | Имя | Описание | Обязательный |
|-----|-----|----------|--------------|
| Path | `projectId` | ID проекта | ✅ |
| Path | `taskId` | ID задачи | ✅ |

**Ответы:**

| HTTP Code | Описание |
|-----------|----------|
| 200 | OK |
| 201 | Created |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |

**Пример запроса:**

```http
POST /open/v1/project/{{projectId}}/task/{{taskId}}/complete HTTP/1.1
Host: api.ticktick.com
Authorization: Bearer {{token}}
```

---

### 5. Удалить задачу

**DELETE** `/open/v1/project/{projectId}/task/{taskId}`

**Параметры:**

| Тип | Имя | Описание | Обязательный |
|-----|-----|----------|--------------|
| Path | `projectId` | ID проекта | ✅ |
| Path | `taskId` | ID задачи | ✅ |

**Ответы:**

| HTTP Code | Описание |
|-----------|----------|
| 200 | OK |
| 201 | Created |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |

**Пример запроса:**

```http
DELETE /open/v1/project/{{projectId}}/task/{{taskId}} HTTP/1.1
Host: api.ticktick.com
Authorization: Bearer {{token}}
```

---

## Project (Проекты/Списки)

### 1. Получить список проектов пользователя

**GET** `/open/v1/project`

**Ответы:**

| HTTP Code | Описание | Schema |
|-----------|----------|--------|
| 200 | OK | `<Project> array` |
| 401 | Unauthorized | - |
| 403 | Forbidden | - |
| 404 | Not Found | - |

**Пример запроса:**

```http
GET /open/v1/project HTTP/1.1
Host: api.ticktick.com
Authorization: Bearer {{token}}
```

**Пример ответа:**

```json
[{
  "id": "6226ff9877acee87727f6bca",
  "name": "project name",
  "color": "#F18181",
  "closed": false,
  "groupId": "6436176a47fd2e05f26ef56e",
  "viewMode": "list",
  "permission": "write",
  "kind": "TASK"
}]
```

---

### 2. Получить проект по ID

**GET** `/open/v1/project/{projectId}`

**Параметры:**

| Тип | Имя | Описание | Обязательный |
|-----|-----|----------|--------------|
| Path | `projectId` | ID проекта | ✅ |

**Ответы:**

| HTTP Code | Описание | Schema |
|-----------|----------|--------|
| 200 | OK | Project |
| 401 | Unauthorized | - |
| 403 | Forbidden | - |
| 404 | Not Found | - |

**Пример запроса:**

```http
GET /open/v1/project/{{projectId}} HTTP/1.1
Host: api.ticktick.com
Authorization: Bearer {{token}}
```

**Пример ответа:**

```json
{
  "id": "6226ff9877acee87727f6bca",
  "name": "project name",
  "color": "#F18181",
  "closed": false,
  "groupId": "6436176a47fd2e05f26ef56e",
  "viewMode": "list",
  "kind": "TASK"
}
```

---

### 3. Получить проект с данными (задачи)

**GET** `/open/v1/project/{projectId}/data`

**⚠️ ВАЖНО:** Этот endpoint возвращает только **незавершенные задачи** (status=0). Завершенные задачи (status=2) не возвращаются!

**Параметры:**

| Тип | Имя | Описание | Обязательный |
|-----|-----|----------|--------------|
| Path | `projectId` | ID проекта | ✅ |

**Ответы:**

| HTTP Code | Описание | Schema |
|-----------|----------|--------|
| 200 | OK | ProjectData |
| 401 | Unauthorized | - |
| 403 | Forbidden | - |
| 404 | Not Found | - |

**Пример запроса:**

```http
GET /open/v1/project/{{projectId}}/data HTTP/1.1
Host: api.ticktick.com
Authorization: Bearer {{token}}
```

**Пример ответа:**

```json
{
  "project": {
    "id": "6226ff9877acee87727f6bca",
    "name": "project name",
    "color": "#F18181",
    "closed": false,
    "groupId": "6436176a47fd2e05f26ef56e",
    "viewMode": "list",
    "kind": "TASK"
  },
  "tasks": [{
    "id": "6247ee29630c800f064fd145",
    "isAllDay": true,
    "projectId": "6226ff9877acee87727f6bca",
    "title": "Task Title",
    "content": "Task Content",
    "desc": "Task Description",
    "timeZone": "America/Los_Angeles",
    "repeatFlag": "RRULE:FREQ=DAILY;INTERVAL=1",
    "startDate": "2019-11-13T03:00:00+0000",
    "dueDate": "2019-11-14T03:00:00+0000",
    "reminders": ["TRIGGER:P0DT9H0M0S", "TRIGGER:PT0S"],
    "priority": 1,
    "status": 0,
    "completedTime": "2019-11-13T03:00:00+0000",
    "sortOrder": 12345,
    "items": [{
      "id": "6435074647fd2e6387145f20",
      "status": 0,
      "title": "Subtask Title",
      "sortOrder": 12345,
      "startDate": "2019-11-13T03:00:00+0000",
      "isAllDay": false,
      "timeZone": "America/Los_Angeles",
      "completedTime": "2019-11-13T03:00:00+0000"
    }]
  }],
  "columns": [{
    "id": "6226ff9e76e5fc39f2862d1b",
    "projectId": "6226ff9877acee87727f6bca",
    "name": "Column Name",
    "sortOrder": 0
  }]
}
```

---

### 4. Создать проект

**POST** `/open/v1/project`

**Параметры (Body):**

| Параметр | Тип | Описание | Обязательный |
|----------|-----|----------|--------------|
| `name` | string | Название проекта | ✅ |
| `color` | string | Цвет проекта | ❌ |
| `sortOrder` | integer | Порядок сортировки | ❌ |
| `viewMode` | string | Режим отображения | ❌ |
| `kind` | string | Тип проекта | ❌ |

**Возможные значения:**

- `viewMode`: `"list"`, `"kanban"`, `"timeline"`
- `kind`: `"TASK"`, `"NOTE"`

**Ответы:**

| HTTP Code | Описание | Schema |
|-----------|----------|--------|
| 200 | OK | Project |
| 201 | Created | - |
| 401 | Unauthorized | - |
| 403 | Forbidden | - |
| 404 | Not Found | - |

**Пример запроса:**

```http
POST /open/v1/project HTTP/1.1
Host: api.ticktick.com
Content-Type: application/json
Authorization: Bearer {{token}}

{
  "name": "project name",
  "color": "#F18181",
  "viewMode": "list",
  "kind": "task"
}
```

**Пример ответа:**

```json
{
  "id": "6226ff9877acee87727f6bca",
  "name": "project name",
  "color": "#F18181",
  "sortOrder": 0,
  "viewMode": "list",
  "kind": "TASK"
}
```

---

### 5. Обновить проект

**POST** `/open/v1/project/{projectId}`

**Параметры:**

| Тип | Имя | Описание | Обязательный |
|-----|-----|----------|--------------|
| Path | `projectId` | ID проекта | ✅ |
| Body | `name` | Название проекта | ❌ |
| Body | `color` | Цвет проекта | ❌ |
| Body | `sortOrder` | Порядок сортировки | ❌ |
| Body | `viewMode` | Режим отображения | ❌ |
| Body | `kind` | Тип проекта | ❌ |

**Ответы:**

| HTTP Code | Описание | Schema |
|-----------|----------|--------|
| 200 | OK | Project |
| 201 | Created | - |
| 401 | Unauthorized | - |
| 403 | Forbidden | - |
| 404 | Not Found | - |

**Пример запроса:**

```http
POST /open/v1/project/{{projectId}} HTTP/1.1
Host: api.ticktick.com
Content-Type: application/json
Authorization: Bearer {{token}}

{
  "name": "Project Name",
  "color": "#F18181",
  "viewMode": "list",
  "kind": "TASK"
}
```

**Пример ответа:**

```json
{
  "id": "6226ff9877acee87727f6bca",
  "name": "Project Name",
  "color": "#F18181",
  "sortOrder": 0,
  "viewMode": "list",
  "kind": "TASK"
}
```

---

### 6. Удалить проект

**DELETE** `/open/v1/project/{projectId}`

**Параметры:**

| Тип | Имя | Описание | Обязательный |
|-----|-----|----------|--------------|
| Path | `projectId` | ID проекта | ✅ |

**Ответы:**

| HTTP Code | Описание |
|-----------|----------|
| 200 | OK |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |

**Пример запроса:**

```http
DELETE /open/v1/project/{{projectId}} HTTP/1.1
Host: api.ticktick.com
Authorization: Bearer {{token}}
```

---

## Модели данных

### Task

| Поле | Тип | Описание | Пример |
|------|-----|----------|--------|
| `id` | string | ID задачи | `"63b7bebb91c0a5474805fcd4"` |
| `projectId` | string | ID проекта | `"6226ff9877acee87727f6bca"` |
| `title` | string | Название задачи | `"Task Title"` |
| `isAllDay` | boolean | Весь день | `true` |
| `completedTime` | string | Время завершения | `"2019-11-13T03:00:00+0000"` |
| `content` | string | Содержимое задачи | `"Task Content"` |
| `desc` | string | Описание чеклиста | `"Task Description"` |
| `dueDate` | string | Дата выполнения | `"2019-11-14T03:00:00+0000"` |
| `items` | array | Подзадачи | `[ChecklistItem]` |
| `priority` | integer | Приоритет задачи | `0` (None), `1` (Low), `3` (Medium), `5` (High) |
| `reminders` | array | Список напоминаний | `["TRIGGER:P0DT9H0M0S", "TRIGGER:PT0S"]` |
| `repeatFlag` | string | Правила повторения | `"RRULE:FREQ=DAILY;INTERVAL=1"` |
| `sortOrder` | integer | Порядок сортировки | `12345` |
| `startDate` | string | Дата начала | `"2019-11-13T03:00:00+0000"` |
| `status` | integer | Статус задачи | `0` (Normal), `2` (Completed) |
| `timeZone` | string | Часовой пояс | `"America/Los_Angeles"` |
| `kind` | string | Тип задачи | `"TEXT"`, `"NOTE"`, `"CHECKLIST"` |

**Важно:**
- `status`: `0` = незавершенная, `2` = завершенная (не `1`!)
- `priority`: `0` = None, `1` = Low, `3` = Medium, `5` = High

---

### ChecklistItem (Подзадача)

| Поле | Тип | Описание | Пример |
|------|-----|----------|--------|
| `id` | string | ID подзадачи | `"6435074647fd2e6387145f20"` |
| `title` | string | Название подзадачи | `"Subtask Title"` |
| `status` | integer | Статус подзадачи | `0` (Normal), `1` (Completed) |
| `completedTime` | string | Время завершения | `"2019-11-13T03:00:00+0000"` |
| `isAllDay` | boolean | Весь день | `false` |
| `sortOrder` | integer | Порядок сортировки | `12345` |
| `startDate` | string | Дата начала | `"2019-11-13T03:00:00+0000"` |
| `timeZone` | string | Часовой пояс | `"America/Los_Angeles"` |

---

### Project

| Поле | Тип | Описание | Пример |
|------|-----|----------|--------|
| `id` | string | ID проекта | `"6226ff9877acee87727f6bca"` |
| `name` | string | Название проекта | `"project name"` |
| `color` | string | Цвет проекта | `"#F18181"` |
| `sortOrder` | integer | Порядок сортировки | `0` |
| `closed` | boolean | Проект закрыт | `false` |
| `groupId` | string | ID группы проекта | `"6436176a47fd2e05f26ef56e"` |
| `viewMode` | string | Режим отображения | `"list"`, `"kanban"`, `"timeline"` |
| `permission` | string | Разрешение | `"read"`, `"write"`, `"comment"` |
| `kind` | string | Тип проекта | `"TASK"`, `"NOTE"` |

---

### ProjectData

| Поле | Тип | Описание |
|------|-----|----------|
| `project` | Project | Информация о проекте |
| `tasks` | array | **Незавершенные задачи** под проектом (только status=0) |
| `columns` | array | Колонки под проектом |

**⚠️ ВАЖНО:** `tasks` в `ProjectData` содержит только незавершенные задачи (status=0). Завершенные задачи (status=2) не возвращаются!

---

### Column

| Поле | Тип | Описание | Пример |
|------|-----|----------|--------|
| `id` | string | ID колонки | `"6226ff9e76e5fc39f2862d1b"` |
| `projectId` | string | ID проекта | `"6226ff9877acee87727f6bca"` |
| `name` | string | Название колонки | `"Column Name"` |
| `sortOrder` | integer | Порядок сортировки | `0` |

---

## Важные замечания

### 1. Получение задач

**Проблема:** Нет единого endpoint для получения всех задач.

**Доступные варианты:**

1. **GET `/open/v1/project/{projectId}/data`** — возвращает только **незавершенные задачи** (status=0)
   - ✅ Работает надежно
   - ❌ Не возвращает завершенные задачи (status=2)

2. **GET `/open/v1/project/{projectId}/task/{taskId}`** — возвращает конкретную задачу
   - ✅ Работает для любой задачи (завершенной и незавершенной)
   - ❌ Требует знания `taskId` и `projectId`

3. **GET `/open/v1/task`** — **НЕ РАБОТАЕТ** (возвращает 500 или 403)

**Рекомендация для поиска задач:**

1. Получить список всех проектов: `GET /open/v1/project`
2. Для каждого проекта получить задачи: `GET /open/v1/project/{projectId}/data`
3. Для поиска конкретной задачи по названию — искать в полученном списке
4. Для завершенных задач — использовать кэш или запрос по `taskId`

---

### 2. Обновление задачи

**⚠️ КРИТИЧЕСКИ ВАЖНО:**

При обновлении задачи через `POST /open/v1/task/{taskId}` **ОБЯЗАТЕЛЬНО** нужно передавать в теле запроса:

```json
{
  "id": "{taskId}",
  "projectId": "{projectId}",
  ...
}
```

Без этих полей запрос может не работать или работать некорректно!

---

### 3. Статусы задач

- `status = 0` — незавершенная задача (Normal)
- `status = 2` — завершенная задача (Completed)
- **НЕ используется** `status = 1` для завершенных задач!

---

### 4. Приоритеты задач

- `priority = 0` — None (по умолчанию)
- `priority = 1` — Low
- `priority = 3` — Medium
- `priority = 5` — High

**Обратите внимание:** значения не последовательные (0, 1, 3, 5), а не (0, 1, 2, 3)!

---

### 5. Формат дат

Все даты должны быть в формате:

```
yyyy-MM-dd'T'HH:mm:ssZ
Пример: "2019-11-13T03:00:00+0000"
```

---

### 6. Напоминания (Reminders)

Формат напоминаний:

```
["TRIGGER:P0DT9H0M0S", "TRIGGER:PT0S"]
```

Где:
- `P0DT9H0M0S` — за 9 часов до события
- `PT0S` — в момент события

---

### 7. Повторяющиеся задачи (Repeat Flag)

Формат RRULE:

```
"RRULE:FREQ=DAILY;INTERVAL=1"
"RRULE:FREQ=WEEKLY;INTERVAL=1"
"RRULE:FREQ=MONTHLY;INTERVAL=1"
```

---

## Проблемы и ограничения API

### 1. Нет endpoint для получения всех задач

**Проблема:** `GET /open/v1/task` не работает (возвращает 500 или 403).

**Решение:** Использовать `GET /open/v1/project/{projectId}/data` для каждого проекта.

---

### 2. Завершенные задачи не возвращаются

**Проблема:** `GET /open/v1/project/{projectId}/data` возвращает только незавершенные задачи (status=0).

**Решение:** 
- Использовать кэш для завершенных задач
- Или запрашивать конкретную задачу по `taskId`: `GET /open/v1/project/{projectId}/task/{taskId}`

---

### 3. Поиск задачи по названию

**Проблема:** Нет endpoint для поиска задачи по названию.

**Решение:**
1. Получить все проекты
2. Для каждого проекта получить задачи через `GET /open/v1/project/{projectId}/data`
3. Искать в полученном списке по названию (с нормализацией)

---

## Контакты и поддержка

Если у вас есть вопросы или отзывы по TickTick Open API, свяжитесь с нами:

- Email: support@ticktick.com
- Developer Center: https://developer.ticktick.com/

---

**Дата создания документации:** 2024-11-04  
**Версия API:** v1  
**Последнее обновление:** 2024-11-04

