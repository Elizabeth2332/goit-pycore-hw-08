from collections import UserDict
from datetime import datetime, date, timedelta
import pickle
import os
import sys


FILENAME = "addressbook.pkl"

def save_data(book, filename: str = FILENAME):
    """Зберегти стан адресної книги у файл (pickle)."""
    with open(filename, "wb") as f:
        pickle.dump(book, f)

def load_data(filename: str = FILENAME):
    """Завантажити стан адресної книги з файлу або повернути порожню, якщо файлу немає/пошкоджений."""
    try:
        with open(filename, "rb") as f:
            return pickle.load(f)
    except (FileNotFoundError, EOFError, pickle.PickleError):
        return AddressBook()
    

# CLASSES

class Field:
    def __init__(self, value: str):
        self.value = value

    def __str__(self):
        return str(self.value)

class Name(Field):
    pass

class Phone(Field):
    def __init__(self, value: str):
        if not (value.isdigit() and len(value) == 10):
            raise ValueError("Phone number must contain exactly 10 digits.")
        super().__init__(value)

class Birthday(Field):
    def __init__(self, value: str):
        try:
            parsed = datetime.strptime(value, "%d.%m.%Y")
        except ValueError:
            raise ValueError("Invalid date format. Use DD.MM.YYYY")
        super().__init__(parsed)

class Record:
    def __init__(self, name):
        self.name = Name(name)
        self.phones = []
        self.birthday = None

    def add_phone(self, phone_number: str):
        self.phones.append(Phone(phone_number))

    def remove_phone(self, phone_number: str):
        self.phones = [p for p in self.phones if p.value != phone_number]

    def edit_phone(self, old_number: str, new_number: str):
        for p in self.phones:
            if p.value == old_number:
                p.value = Phone(new_number).value
                return
        raise ValueError("Old number not found.")

    def find_phone(self, phone_number: str):
        for p in self.phones:
            if p.value == phone_number:
                return p.value
        return None

    # ADD FUNCTION add_birthday
    def add_birthday(self, birthday_str: str):
        self.birthday = Birthday(birthday_str)

    def __str__(self):
        phones_str = "; ".join(p.value for p in self.phones) if self.phones else "—"
        birthday_str = f", birthday: {self.birthday.value.strftime('%d.%m.%Y')}" if self.birthday else ""
        return f"Contact name: {self.name.value}, phones: {phones_str}{birthday_str}"

class AddressBook(UserDict):
    def add_record(self, record: 'Record'):
        self.data[record.name.value] = record

    def find(self, name: str) -> 'Record | None':
        return self.data.get(name)

    def delete(self, name: str):
        if name in self.data:
            del self.data[name]

    def get_upcoming_birthdays(self):
        """
        Find all users whose birthdays are within the next 7 days (including today).
        If a birthday falls on a weekend, shift it to the next Monday.
        """
        today = date.today()
        upcoming = []

        for record in self.data.values():
            if not record.birthday:
                continue

            bday = record.birthday.value.date()
            try:
                bday_this_year = bday.replace(year=today.year)
            except ValueError:
                # Feb 29 on a non-leap year -> Feb 28
                bday_this_year = date(today.year, 2, 28)

            if bday_this_year < today:
                try:
                    bday_this_year = bday.replace(year=today.year + 1)
                except ValueError:
                    bday_this_year = date(today.year + 1, 2, 28)

            days_ahead = (bday_this_year - today).days

            if 0 <= days_ahead <= 7:
                if bday_this_year.weekday() == 5:      # Saturday
                    bday_this_year = bday_this_year + timedelta(days=2)
                elif bday_this_year.weekday() == 6:    # Sunday
                    bday_this_year = bday_this_year + timedelta(days=1)

                upcoming.append({
                    "name": record.name.value,
                    "congratulation_date": bday_this_year.strftime("%Y.%m.%d"),
                })

        return upcoming

# DEMO SEED (якщо книга порожня)
def seed_sample_contacts(book: AddressBook):
    if book.data:
        return  # не дублюємо дані, якщо вже є завантажені контакти

    john_record = Record("John")
    john_record.add_phone("1234567890")
    john_record.add_phone("5555555555")
    john_record.add_birthday("04.11.1975")
    book.add_record(john_record)

    jane_record = Record("Jane")
    jane_record.add_phone("9876543210")
    jane_record.add_birthday("04.11.1975")
    book.add_record(jane_record)

# CLI 
def parse_input(user_input: str):
    cmd, *args = user_input.strip().split()
    return cmd.lower(), args

def input_error(func):
    def inner(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValueError:
            return "Give me correct data, please."
        except KeyError:
            return "Contact not found."
        except IndexError:
            return "Not enough arguments."
    return inner

@input_error
def add_contact(args, book: AddressBook):
    # add <name> <phone>
    name, phone, *_ = args
    record = book.find(name)
    msg = "Contact updated."
    if record is None:
        record = Record(name)
        book.add_record(record)
        msg = "Contact added."
    if phone:
        record.add_phone(phone)
    return msg

@input_error
def change_contact(args, book: AddressBook):
    # change <name> <old_phone> <new_phone>
    name, old_phone, new_phone, *_ = args
    record = book.find(name)
    if record is None:
        raise KeyError
    record.edit_phone(old_phone, new_phone)
    return "Contact updated."

@input_error
def show_phone(args, book: AddressBook):
    # phone <name>
    name, *_ = args
    record = book.find(name)
    if record is None:
        raise KeyError
    if not record.phones:
        return "No phones saved."
    return ", ".join(p.value for p in record.phones)

@input_error
def show_all(args, book: AddressBook):
    # all
    if not book.data:
        return "No contacts yet."
    return "\n".join(str(rec) for rec in book.data.values())

@input_error
def add_birthday(args, book: AddressBook):
    # add-birthday <name> <DD.MM.YYYY>
    name, bday_str, *_ = args
    record = book.find(name)
    if record is None:
        record = Record(name)
        book.add_record(record)
        msg = "Contact created and birthday added."
    else:
        msg = "Birthday added."
    record.add_birthday(bday_str)
    return msg

@input_error
def show_birthday(args, book: AddressBook):
    # show-birthday <name>
    name, *_ = args
    record = book.find(name)
    if record is None:
        raise KeyError
    if not record.birthday:
        return "No birthday set."
    return record.birthday.value.strftime("%d.%m.%Y")

@input_error
def birthdays(args, book: AddressBook):
    # birthdays
    upcoming = book.get_upcoming_birthdays()
    if not upcoming:
        return "No birthdays in the next 7 days."
    lines = [f"{it['congratulation_date']}: {it['name']}" for it in upcoming]
    return "\n".join(lines)

# MAIN
def main():
    # 1) спроба відновити дані з файлу
    book = load_data()

    # 2) опціонально насіяти демо-контакти лише якщо книга порожня (перший запуск)
    seed_sample_contacts(book)

    print("Welcome to the assistant bot!")
    print(f"(Loaded {len(book.data)} contacts from '{FILENAME}'\n)")

    try:
        while True:
            user_input = input("Enter a command: ").strip()
            if not user_input:
                continue

            command, args = parse_input(user_input)

            if command in ("close", "exit"):
                print("Good bye!")
                break
            elif command == "hello":
                print("How can I help you?")
            elif command == "add":
                print(add_contact(args, book))
            elif command == "change":
                print(change_contact(args, book))
            elif command == "phone":
                print(show_phone(args, book))
            elif command == "all":
                print(show_all(args, book))
            elif command == "add-birthday":
                print(add_birthday(args, book))
            elif command == "show-birthday":
                print(show_birthday(args, book))
            elif command == "birthdays":
                print(birthdays(args, book))
            else:
                print("Invalid command.")
    except KeyboardInterrupt:
        print("\nInterrupted. Saving and exiting...")
    finally:
        # 3) гарантовано зберегти перед виходом (у т.ч. при Ctrl+C або винятках)
        try:
            save_data(book)
            print(f"Data saved to '{FILENAME}'.")
        except Exception as e:
            print(f"Failed to save data: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()