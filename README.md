# Командный кейс No 5 «Разработка распределенного хранилища данных»
> Московская предпрофессиональная олимпиада Профиль «Информационные технологии»

## Cборка проекта
### Сборка сервера
````shell 
git clone https://github.com/Cyber-Zhaba/storage
cd storage/Storage
docker compose up -d
 ````
### Сборка сайта
````shell 
git clone https://github.com/Cyber-Zhaba/storage
cd storage/WebApp
docker compose up -d
 ````

## Оглавление
1. [Цель](#Цель)
2. [Задачи](#Задачи)
3. [Логика и структурные схемы](#Логика-и-структурные-схемы)
4. [Хранение](#Хранение)
5. [Основные алгоритмы](#Основные-алгоритмы)
    1. [Добавление файла](#добавление-файла)
    2. [Удаление файла](#удаление-файла)
    3. [Получить файд](#получить-файл)
    4. [Поиск подстроки](#поиск-подстроки)
    5. [Добавление сервера](#добавление-сервера)
6. [Тестирование](#тестирование)
7. [Значения кода лога](#значения-кода-лога)

## Цель:
- Разработать веб-приложения, представляющее собой распределенное хранилище данных для хранения текстовых файлов и выполнения полнотекстового поиска.
## Задачи:
- [X] Создание интерфейса администратора и пользователя
    - [X] Регистрация, вход
    - [X] Поиск
    - [X] Изменение данных файла
    - [X] Загрузка файлов
    - [X] Создание возможностей администратора
      - [X] Просмотр всех файлов
      - [X] Подключение и удаление, просмотр информации о серверах
      - [X] Возможность изменение данных любых файлов
      - [X] Просмотор действий пользователей
      - [X] Изменение данных пользователей
- [X] Реализация функции поиска данных
    - [X] Получить список серверов с актуальной версией файла
    - [X] Разбить файлы по строкам и ассинхроно отправить задачу на поиск серверам
    - [X] Собрать ответ
- [X] Разработка системы, состоящей из центрального сервера и серверов-хранилищ
    - [X] Сервер хранилища
       - [X] Обеспечение дублирования данных на серверах-хранилищах
    - [X] Центральный сервер
      - [X] Базы данных для: документов, пользователей, серверов
      - [X] Управление действиями серверов-хранилищ через центральный сервер.


# Логика и структурные схемы
```mermaid
sequenceDiagram

    participant User

    participant Central Server

    participant Storage Communicator

    participant DataBase API

    participant Storages

  
  
  

    User->>Central Server: Operation with user data

    activate Central Server

  

    Central Server -->> DataBase API: request

    activate DataBase API

    DataBase API -->> Central Server: response

    deactivate DataBase API

  

    Central Server -->> User: response

    deactivate Central Server

  

    User->> Central Server: Operation with files

    activate Central Server

  

    Central Server -->> DataBase API: get list of available servers

    activate DataBase API

    DataBase API -->> Central Server: response

    deactivate DataBase API

  

    Central Server -->> Storage Communicator: request

    activate Storage Communicator

    Storage Communicator -->> Storages: async requests

    activate Storages

    Storages -->> Storage Communicator: response

    deactivate Storages

    Storage Communicator -->> Central Server: response

    deactivate Storage Communicator

    Central Server -->> DataBase API: update data

    Central Server ->> User: response

  

    deactivate Central Server
```
Обработка запросов от пользователя производится на Центральном Сервере. Запросы не связанные с взаимодействие с файлами, переадресовываются на сторону базы данных через разработанную систему API. Запросы связанные с взаимодействием с файлами сначала обрабатываются на Центральном Сервере, после проверки данных запрос переадресовывается на сторону Коммуникатора с Хранилищами. Запросы от Коммуникатора асинхронно отправляются к Хранилищам посредствам TCP запроса. Результаты выполнения операций на стороне Хранилищ собираются на стороне Коммуникатора, после чего возвращаются Центральному Серверу. Далее результаты обрабатываются, если необходимо, то вносятся изменения в базу данных. В результате формируется ответ, который возвращается пользователю. 
## Хранение
### Хранение файлов
```mermaid
---

title: Storage structure

---
classDiagram
    Root <|-- Storage
    note for Storage "Functions
- Add()
- Delete()
- Get()
- Find()
- AddServer()
- End()
- Info()
 - Ping()
  "

    Root --|> File

    Root : files

    Root : operations_with_files()

    class Storage{

        str host

        int port

        int capacity

        server.serv_forever()

    }

  

    class File{

        str filename

        int size

        read()

        write()

    }
```
Файлы описывается размером и именем и поддерживает два протокола взаимодействия: чтение и запись. Каждый файл размещённый в хранилище получает уникальное имя, чтобы избежать коллизий с уже существующими файлами. Все файлы хранятся в подпапке root, размещенной в каталоге проекта. Хранилище посредством TCP запроса принимает команды для выполнений операций с файлами. Тип операции и её корректность определяются на стороне Центрального Сервера.
### Структура баз данных
![Alt-текст](https://github.com/Cyber-Zhaba/storage/assets/94627168/caef82cd-0e95-4011-a0b4-cbc8fab9e3bd "Орк")
## Основные алгоритмы
Здесь и далее мы будем рассматривать примеры с четырьмя хранилищами, однако в реальности количество хранилищ может быть любым и операции с хранилищами будут масштабироваться в соответствии с их количеством.
### Добавление файла
```mermaid
gantt

    dateFormat sss

    axisFormat %L ms

    section Central Server

        Download File  :a1, 1, 0.002s

        Request to DB :a2, after a1, 0.001s

    section DataBase

        Compute Respons :a3, after a2, 0.001s

        Log Changes :after a3, 0.001s

    section Storage Communicator

        Send Requests to Storages :a4, after a3, 0.002s

    section Storages

        Add File :after a4, 0.002s

        Add File :after a4, 0.002s

        Add File :after a4, 0.002s

        Add File :after a4, 0.002s
```
### Удаление файла
```mermaid
gantt

    dateFormat sss

    axisFormat %L ms

    section Central Server

        Request to DB :a2, 0, 0.001s

    section DataBase

        Compute Respons :a3, after a2, 0.001s

        Log Changes :after a3, 0.001s

    section Storage Communicator

        Send Requests to Storages :a4, after a3, 0.002s

    section Storages

        Delete File :after a4, 0.001s

        Delete File :after a4, 0.001s

        Delete File :after a4, 0.001s

        Delete File :after a4, 0.001s
```
### Получить файл
```mermaid
gantt

    dateFormat sss

    axisFormat %L ms

    section Central Server

        Request :a1, 1, 0.001s

        Response :after c1, 0.001s

    section Storage Communicator

        Request to Storages :b1, after a1, 0.001s

    section Storages

        Send File :c1, after b1, 0.002s
```
### Поиск подстроки
```mermaid
gantt
    dateFormat sss
    axisFormat %L ms
    section Central Server
        Request :a1, 1, 0.001s
        Response :after b4, 0.001s
    section Storage Communicator
        Split tasks :b1, after a1, 0.001s
        Send Request :b2, after b1, 0.001s
        Process Result :b3, after c1, 0.001s
        Return Respnonse :b4, after b3, 0.001s
    section Storages
        Look for substring :after b2, 0.002s
        Look for substring :after b2, 0.002s
        Look for substring :after b2, 0.002s
        Look for substring :c1, after b2, 0.002s
```
### Добавление сервера
```mermaid
gantt

    dateFormat sss

    axisFormat %L ms

    section Central Server

        Request :a1, 1, 0.001s
        Response :a2, after b2, 0.001s

    section DataBase

        Compute Response :b1, after a1, 0.001s

        log :after b1, 0.001s

        Update data :b2, after c2, 0.001s

        log :after b2, 0.001s

    section Storage Communicator

        request to storage :c1, after b1, 0.001s

        response from storage :c2, after e1, 0.001s

    section Old Storage

        Connect :d1, after c1, 0.001s

        Send all Files :d2, after d1, 0.002s

    section New Storage

        Recieve Files :e1, after d1, 0.002s
```
## Тестирование
 - [![Тут текст](адрес до картинки)](ссылка на страничку YouTube)
## Значения кода лога
| Тип |               Описание                |
|----:|:-------------------------------------:|
|   0 |             Регистраиция              |
|   1 |         Успешная авторизация          |
|   2 |             Попытка входа             |
|   3 |                 Выход                 |
|   4 |     Изменение данных пользователя     |
|   5 |           Добавление файла            |
|   6 |            Изменение файла            |
|   7 |            Удаление файла             |
|   8 |          Добавление сервера           |
|   9 | Остановка/отключение/удаление сервера |
|  10 |           Включение сервера           |
