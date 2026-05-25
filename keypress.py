"""
Модуль для неблокуючого детектування натискання клавіш (keypress.py).

Цей модуль дозволяє відстежувати натискання клавіші Пробіл під час роботи скрапера
без зупинки основного процесу збору даних. Він містить клас KeypressDetector,
який автоматично адаптується під операційні системи Windows та Linux/macOS.
Написано простою мовою з детальними коментарями.
"""

import sys

# Якщо це Unix-подібна система (macOS або Linux), імпортуємо бібліотеки для роботи з терміналом
if sys.platform != "win32":
    import termios
    import tty
    import select


class KeypressDetector:
    """
    Клас, що дозволяє виявити, чи натиснув користувач клавішу Пробіл у консолі.
    Працює у фоновому неблокуючому режимі (програма не зависає в очікуванні натискання).
    """

    def __init__(self, active=True):
        """
        Ініціалізує детектор клавіш.

        Параметри:
            active (bool): Якщо True, активує детектор (тільки якщо термінал підтримує інтерактивний ввід).
        """
        # Детектор працює лише якщо ввід здійснюється в інтерактивному терміналі (tty)
        self.active = active and sys.platform != "win32" and sys.stdin.isatty()
        if self.active:
            try:
                self.fd = sys.stdin.fileno()
                # Зберігаємо старі налаштування терміналу, щоб повернути їх при виході
                self.old_settings = termios.tcgetattr(self.fd)
                # Переводимо термінал у режим cbreak (символи зчитуються миттєво без очікування натискання Enter)
                tty.setcbreak(self.fd)
            except Exception:
                self.active = False
            
    def check_space(self):
        """
        Перевіряє, чи натиснув користувач клавішу Пробіл.
        Не блокує виконання коду: якщо клавішу не натиснуто, метод просто повертає False.

        Повертає:
            bool: True, якщо натиснуто Пробіл, інакше False.
        """
        # Сценарій для Windows
        if sys.platform == "win32":
            try:
                import msvcrt
                # Перевіряємо, чи є в черзі натиснута клавіша
                if msvcrt.kbhit():
                    ch = msvcrt.getch()
                    # Перевіряємо, чи це пробіл
                    if ch == b' ':
                        return True
            except Exception:
                pass
            return False
            
        # Сценарій для macOS та Linux
        try:
            # Використовуємо select для неблокуючої перевірки наявності даних у стандартному потоці вводу (stdin)
            rlist, _, _ = select.select([sys.stdin], [], [], 0)
            if rlist:
                ch = sys.stdin.read(1)
                # Перевіряємо, чи зчитаний символ є пробілом
                if ch == ' ':
                    return True
        except Exception:
            pass
        return False
        
    def restore(self):
        """
        Повертає налаштування терміналу macOS/Linux у початковий стан.
        Це критично зробити перед тим, як виводити нове інтерактивне меню (наприклад, input()),
        інакше ввід працюватиме некоректно.
        """
        if self.active:
            try:
                termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old_settings)
            except Exception:
                pass
