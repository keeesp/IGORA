from io import BytesIO

import barcode
from barcode import EAN13
from barcode.writer import ImageWriter
import img2pdf

from facade import Facade
import random

from PyQt5.QtGui import QFont, QPixmap
from PyQt5 import QtWidgets
from PyQt5 import uic, QtCore, QtGui
from PyQt5.QtCore import Qt, QTimer, QTime, QDateTime
from PyQt5.QtWidgets import QGraphicsScene, QListWidgetItem
from PyQt5.QtWidgets import QMainWindow, QApplication, QTableWidget, QTableWidgetItem, QDialog

import sys
import time
import datetime

import logging

from PyQt5.QtWidgets import QMessageBox

logging.basicConfig(level=logging.INFO)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.facade = Facade()
        self.ui = uic.loadUi("main.ui", self)
        self.page = self.ui.stackedWidget_main
        self.page_id = [0]  # тут будут индексы доступных страничек после авторизации для сотрудника
        self.now_page = 0

        self.time = QtCore.QTime(0, 10, 0)

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.Counter)

        self.page.setCurrentIndex(self.page_id[self.now_page])
        self.ui.btn_next.clicked.connect(self.next_page)
        self.ui.btn_back.clicked.connect(self.back_page)
        self.ui.btn_all_clients.clicked.connect(self.page_all_clients)
        self.ui.btn_exit.clicked.connect(lambda: self.exit(False))

        self.ui.btn_new_serv.clicked.connect(self.new_service)
        self.ui.btn_delete_serv.clicked.connect(self.delete_service)
        self.ui.btn_save_serv.clicked.connect(self.save_service)

        self.build_combobox_clients()
        self.build_combobox_services()

        self.ui.btn_new_order.clicked.connect(self.add_new_request)
        self.ui.btn_save_request.clicked.connect(self.save_request)
        self.ui.btn_plus.clicked.connect(self.add_service_to_request)
        # self.ui.btn_code.clicked.connect(self.generateCode)

        self.ui.btn_new_client.clicked.connect(self.oped_new_client)

        self.updateTableServ()
        self.updateTableHistory()
    def Counter(self):
        self.time = self.time.addSecs(-1)
        self.lcdTimer.display(self.time.toString("hh:mm:ss"))
        if self.time == QTime(0, 2, 0):
            self.messagebox = QMessageBox(self)
            self.messagebox.setWindowTitle("Внимание!")
            self.messagebox.setText("До завершения сеанса осталось 2 минуты!")
            self.messagebox.setStandardButtons(QMessageBox.Ok)
            self.messagebox.show()

        if self.time == QTime(0, 0, 0):
            self.window().exit(False)
            self.timer.stop()

    def exit(self, block):
        self.now_page = 0
        self.page.setCurrentIndex(self.page_id[self.now_page])
        t = time.localtime()
        time_string = time.strftime("%d:%m:%Y %H:%M:%S", t)  # время выхода
        self.facade.insert_time_exit(self.now_login, time_string, block)
        self.hide()
        self.open_auth()

    def page_new_clients(self):
        self.toTable()
        self.page.setCurrentIndex(3)


    def next_page(self):
        if self.now_page != len(self.page_id)-1:
            self.now_page += 1
            self.page.setCurrentIndex(self.page_id[self.now_page])

    def back_page(self):
        if self.now_page != 0:
            self.now_page -= 1
            self.page.setCurrentIndex(self.page_id[self.now_page])

    def open_auth(self):

        dialog = DialogAuth(self)
        dialog.setWindowTitle("Авторизация")
        dialog.show()
        dialog.exec_()

    def oped_new_client(self):
        dialog_client = DialogNewClient(self)
        dialog_client.setWindowTitle("Добавление нового клиента")
        dialog_client.show()
        dialog_client.exec_()


class DialogAuth(QDialog):
    def __init__(self, parent=None):
        super(DialogAuth, self).__init__(parent)
        self.ui = uic.loadUi("auth.ui", self)
        self.facade = Facade()

        self.scene = QGraphicsScene(0, 0, 300, 80)
        self.ui.draw_captcha.setScene(self.scene)
        self.ui.btn_enter.clicked.connect(self.enter)
        self.ui.btn_new_captcha.clicked.connect(self.captcha_generation)
        self.ui.btn_hide_password.clicked.connect(self.vis_pas)
        self.visible_captcha(False)

        self.count_try_entry = 0
        self.now_captcha = None
        self.next_try = 0
        self.vis_p = False

    def vis_pas(self):
        ed = self.ui.edit_password
        if self.vis_p:
            self.vis_p = False
            ed.setEchoMode(QtWidgets.QLineEdit.Password)
        else:
            self.vis_p = True
            ed.setEchoMode(QtWidgets.QLineEdit.Normal)

    def visible_captcha(self, visible=True):

        self.ui.draw_captcha.setVisible(visible)
        self.ui.edit_captcha.setVisible(visible)
        self.ui.label_4.setVisible(visible)
        self.ui.btn_new_captcha.setVisible(visible)

    def captcha_generation(self):
        self.scene.clear()
        syms = 'qwertyuiopasdfghjklzxcvbnm1234567890'
        count_syms = 3
        now_syms = ['']*count_syms
        x, y = 30, 20

        self.scene.addLine(0, random.randint(20, 45), 200, random.randint(30, 60))

        for i in range(count_syms):
            now_syms[i] = syms[random.randint(0, 35)]
            x+=20
            text = self.scene.addText(f"{now_syms[i]}")
            text.setFont(QFont("MS Shell Dlg 2", 15))
            text.moveBy(x, y+random.randint(-10, 20))
        self.now_captcha = ''.join(now_syms)

    def mes_box(self, text):
        self.messagebox = QMessageBox(self)
        self.messagebox.setWindowTitle("Ошибка")
        self.messagebox.setText(text)
        self.messagebox.setStandardButtons(QMessageBox.Ok)
        self.messagebox.show()

    def enter(self):

        t = time.localtime()
        now_time = time.mktime(t)  # переводим в секунды
        auth_log = self.ui.edit_login.text()
        auth_pas = self.ui.edit_password.text()

        if auth_log == '' or auth_pas == '':
            logging.log(logging.INFO, 'Ошибка. Заполните все поля!')
            self.mes_box('Заполните все поля!')

        elif self.now_captcha is not None and self.ui.edit_captcha.text() == '':    # если капча существует и она не пустая
            logging.log(logging.INFO, 'Ошибка. Введите капчу!')
            self.mes_box('Введите капчу!')
        else:
            password, role, last_exit, block, fio, photo = self.parent().facade.get_for_authorization(auth_log)
            pix = QPixmap(f'img/Ширяев.jpeg')
            if last_exit is not None and block:     # после окончания предыдущей сессии, новую можно начать только через 3 минуты
                last_exit = last_exit.split()
                day, mon, year = map(int, last_exit[0].split(':'))
                hour, mi, sec = map(int, last_exit[1].split(':'))
                time_block = time.mktime((year, mon, day, hour, mi+3, sec, 0, 0, 0))    # переводим в секунды с учетом 3х минут блокировки
                if time_block > now_time:
                    logging.log(logging.INFO, 'Ошибка. Подождите, время нового сеанса еще не пришло.')
                    self.mes_box('Подождите, время нового сеанса еще не пришло.')
                    return

            if self.count_try_entry >= 3 and self.next_try > now_time:    # не прошло 10 секунд с прошлой попытки входа (после 3 неуспешной попытки)
                logging.log(logging.INFO, 'Ошибка. Подождите, прежде чем пытаться вводить снова.')
                self.mes_box('Подождите, прежде чем пытаться вводить снова.')
                return

            if self.now_captcha is not None and self.now_captcha != self.ui.edit_captcha.text():
                logging.log(logging.INFO, 'Ошибка. Неправильно введена капча.')
                self.mes_box('Неправильно введена капча.')
            elif password != auth_pas:    # неправильный пароль или вернул пустую строку тк нет такого логина
                self.count_try_entry += 1
                if self.count_try_entry >= 3:
                    self.next_try = now_time+10
                if password != '':  # если нет пароля, значит нет пользователя с введенным логином, поэтому записывать в историю входа не надо
                    time_entry = time.strftime("%d:%m:%Y %H:%M:%S", t)    # время неуспешной попытки входа
                    self.parent().facade.insert_time_entry(auth_log, time_entry, False)

                if self.count_try_entry == 2:
                    self.visible_captcha(True)
                    self.captcha_generation()
                    logging.log(logging.INFO, 'Ошибка. Вторая неуспешная попытка входа. Теперь введите капчу.')
                    self.mes_box('Вторая неуспешная попытка входа. Теперь введите капчу.')
                else:
                    logging.log(logging.INFO, 'Ошибка. Неправильно введены данные.')
                    self.mes_box('Неправильно введены данные.')
            elif password == auth_pas:
                time_entry = time.strftime("%d:%m:%Y %H:%M:%S", t)    # время успешной попытки входа
                self.parent().facade.insert_time_entry(auth_log, time_entry, True)
                logging.log(logging.INFO, 'Вход выполнен')
                self.parent().ui.lbl_fio.setText(fio)
                self.parent().ui.lbl_role.setText(role)
                if role == 'Старший смены' or role == 'Продавец':
                    self.parent().hide()
                    self.parent().page_id = [0, 2]
                    """Передать индексы страничек"""
                else:   # администратор
                    self.parent().hide()
                    self.parent().page_id = [0, 1, 4, 5]
                self.parent().show()
                self.parent().ui.lbl_photo.setPixmap(pix)
                self.parent().timer.start(1000)
                self.parent().now_login = auth_log
                self.close()


class DialogNewClient(QDialog):
    def __init__(self, parent=None):
        super(DialogNewClient, self).__init__(parent)
        self.ui = uic.loadUi("new_client.ui", self)
        self.facade = Facade()

        self.ui.btn_add_client.clicked.connect(self.add)

    def add(self):
        self.email = self.ui.edit_email.text()
        self.fio = self.ui.edit_fio.text()
        self.address = self.ui.edit_address.text()
        self.dateOfBirth = self.ui.date_birth.dateTime().toString('dd.MM.yyyy')
        self.passportData = self.ui.edit_passport.text()

        if self.fio != '' and self.passportData != '' and self.dateOfBirth != '' and self.address != '' and self.email != '':
            self.facade.insert_client(self.fio, self.passportData, self.dateOfBirth, self.address, self.email)
        else:
            self.mes_box('Заполните все поля!')

    def mes_box(self, text):
        self.messagebox = QMessageBox(self)
        self.messagebox.setWindowTitle("Ошибка")
        self.messagebox.setText(text)
        self.messagebox.setStandardButtons(QMessageBox.Ok)
        self.messagebox.show()


class Builder:
    def __init__(self):
        self.qapp = QApplication(sys.argv)
        self.window = MainWindow()
        self.auth()

    def auth(self):
        self.window.open_auth()
        self.qapp.exec()


if __name__ == '__main__':
    B = Builder()