import os
import time

import pymysql


def main():
    wait_for_mysql()
    if database_is_empty():
        from seed import main as seed_database

        seed_database()

    from app import create_app

    create_app().run(host="0.0.0.0", port=5000, debug=False)


def wait_for_mysql():
    for _ in range(60):
        try:
            connection = connect()
            connection.close()
            return
        except pymysql.MySQLError:
            time.sleep(2)
    raise SystemExit("Baza MySQL nie odpowiada.")


def database_is_empty():
    name = os.environ.get("MYSQL_DATABASE", "dental_clinic")
    try:
        connection = connect(name)
    except pymysql.MySQLError:
        return True
    try:
        with connection.cursor() as cursor:
            cursor.execute("SHOW TABLES LIKE 'users'")
            return cursor.fetchone() is None
    finally:
        connection.close()


def connect(database=None):
    return pymysql.connect(
        host=os.environ.get("MYSQL_HOST", "db"),
        port=int(os.environ.get("MYSQL_PORT", "3306")),
        user=os.environ.get("MYSQL_USER", "root"),
        password=os.environ.get("MYSQL_PASSWORD", ""),
        database=database,
        charset="utf8mb4",
    )


if __name__ == "__main__":
    main()
