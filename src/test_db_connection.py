import os

import mysql.connector
from dotenv import load_dotenv


def test_connection():

    load_dotenv()

    print("=" * 65)
    print("TESTING PYTHON -> MYSQL CONNECTION")
    print("=" * 65)

    connection = None

    try:

        connection = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            port=int(os.getenv("DB_PORT", 3306)),
            database=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
        )

        if connection.is_connected():

            print("\nConnection successful.")

            cursor = connection.cursor()

            cursor.execute(
                "SELECT DATABASE(), VERSION();"
            )

            database_name, mysql_version = cursor.fetchone()

            print(
                f"Connected database: {database_name}"
            )

            print(
                f"MySQL version: {mysql_version}"
            )

            cursor.execute(
                "SHOW TABLES;"
            )

            tables = [
                row[0]
                for row in cursor.fetchall()
            ]

            print(
                "\nTables found:"
            )

            for table in tables:
                print(f" - {table}")

            cursor.close()

    except mysql.connector.Error as error:

        print(
            f"\nConnection failed: {error}"
        )

        raise

    finally:

        if (
            connection is not None
            and connection.is_connected()
        ):

            connection.close()

            print(
                "\nConnection closed successfully."
            )


if __name__ == "__main__":
    test_connection()
    