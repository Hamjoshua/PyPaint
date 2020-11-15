import sys
import sqlite3
import re
from csv import DictReader
from math import acos, sqrt, degrees
from random import randrange

from PyQt5 import QtCore
from PyQt5.QtGui import *
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget
from PyQt5.QtWidgets import QButtonGroup, QLabel, QTextBrowser
from PyQt5.QtWidgets import QInputDialog, QFileDialog, QColorDialog, \
    QMessageBox, QListWidgetItem

from PyQt5 import uic

SELECTION_PEN = QPen(QColor(0xff, 0xff, 0xff), 1, QtCore.Qt.DashLine)
MAKE_FORM_PEN = QPen(QColor(0xff, 0xff, 0xff), 1, QtCore.Qt.SolidLine)

COLORS = ['#000000', '#880016', '#ED1B24', '#FF7F26',
          '#FEF200', '#21B24D', '#00A3E8', '#3F47CC',
          '#FFFFFF', '#C3C3C3', '#B97A57', '#FFC90D',
          '#EFE4AE', '#B5E51D', '#C7BFE6', '#A349A3']

DEFAULT_COLORS = ['#000000', '#FFFFFF']


class History:
    def __init__(self, some_value=None):
        if some_value:
            self.history = list(some_value)
        else:
            self.history = []
        self.count = 0

    def next(self):
        if self.count + 1 < len(self.history):
            self.count += 1
            return self.history[self.count]
        return 404

    def back(self):
        if self.count - 1 > -1:
            self.count -= 1
            return self.history[self.count]
        return 404

    def add(self, num):
        self.history = self.history[:self.count + 1]
        self.history.append(num)
        if len(self.history) > 10:
            self.history = self.history[1:]
        self.count = len(self.history) - 1

    def __repr__(self):
        return str(self.history) if self.history else 'History is empty'

    def __str__(self):
        return self.__repr__()


class MainWindow(QMainWindow):  # , Ui_Form
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        uic.loadUi('MainWindow.ui', self)
        self.setWindowTitle('PyPaint')
        self.setWindowIcon(QIcon('icons/main_icon.ico'))

        self.tools_group = QButtonGroup(self)
        self.connecting_buttons()

        # Tools settings
        self.active_color = self.main_color_btn_1
        self.get_main_color = \
            {self.main_color_btn_1: DEFAULT_COLORS[0],
             self.main_color_btn_2: DEFAULT_COLORS[1]}

        self.font = QFont(self.fontComboBox.currentText())
        self.current_text = ''
        self.text_size = 12

        self.tool_size = self.change_size_spinBox.value()
        self.active_tool = None

        # Set brush active with the start project
        self.brush.click()

        # Auxiliary variables
        self.is_drawed_line_for_curve = False
        self.polygon_points = []
        self.rect_for_draw = QtCore.QRect()
        self.is_text_can_writed = False

        self.file_extensions = "All Files (*.png *.jpg);;JPG (*.jpg);;PNG (*.png)"
        self.default_sizes_of_created_image = \
            [f'{lg} * {lg * 3 // 4}' for lg in range(400, 1200, 200)]
        self.difference_size = \
            (self.width() - self.image.width(),
             self.height() - self.image.height())

        # Init default image
        self.pixmap = QPixmap(800, 600)
        self.pixmap.fill(QColor('#FFFFFF'))
        self.current_pixmap = self.pixmap.copy()
        self.temp_pixmap = self.pixmap.copy()
        self.current_file_name = False
        self.image.setPixmap(self.pixmap)
        self.canvas_history = History()
        self.layers_dict = dict()
        self.add_layer(priority='Main')
        self.add_to_history()
        self.update_image_by_window_size()
        self.priority = None

        # Active pen for tools
        self.regularly_pen = QPen(
            QColor(self.get_main_color[self.active_color]), self.tool_size,
            QtCore.Qt.SolidLine, QtCore.Qt.SquareCap, QtCore.Qt.MiterJoin)

        self.firstPoint = QtCore.QPoint()
        self.lastPoint = QtCore.QPoint()

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.show_layers)
        self.timer.start(1)

    def connecting_buttons(self):
        # Init triggers for buttons in file_menu
        self.create_btn.triggered.connect(self.newFileDialog)
        self.open_btn.triggered.connect(self.openFileNameDialog)
        self.save_btn.triggered.connect(self.saveFileDialog)
        self.save_as_btn.triggered.connect(self.save_asFileDialog)
        self.exit_btn.triggered.connect(exit)

        # Init triggers for buttons in image_menu
        self.flip_gorizontally_btn.triggered.connect(self.flip_gorizontally_image)
        self.flip_vertically_btn.triggered.connect(self.flip_vertically_image)
        self.turn_90_right_btn.triggered.connect(lambda: self.turn_image(90))
        self.turn_90_left_btn.triggered.connect(lambda: self.turn_image(270))
        self.turn_180_btn.triggered.connect(lambda: self.turn_image(180))

        # Init triggers for buttons in info_menu
        self.info_btn.triggered.connect(self.show_info_form)

        # Init triggers for buttons in tools_for_image_frame
        self.tools_group.addButton(self.select)
        self.crop_image_btn.clicked.connect(self.crop_image)
        self.clean_selection_btn.clicked.connect(self.clean_selection)

        # Adding buttons to tools_group
        self.tools_group.addButton(self.brush)
        self.tools_group.addButton(self.pencil)
        self.tools_group.addButton(self.text)
        self.tools_group.addButton(self.filling)
        self.tools_group.addButton(self.pipette)
        self.tools_group.addButton(self.eraser)
        self.tools_group.addButton(self.drawLine)
        self.tools_group.addButton(self.drawCurveLine)
        self.tools_group.addButton(self.drawEllipse)
        self.tools_group.addButton(self.drawRect)
        self.tools_group.addButton(self.drawRoundedRect)
        self.tools_group.addButton(self.drawPolygon)
        self.tools_group.buttonClicked.connect(self.change_tool)

        # Init history buttons
        self.go_next.triggered.connect(self.next_history)
        self.go_back.triggered.connect(self.back_history)

        # Init triggers for widgets in tool_settings_frame
        self.change_size_spinBox.valueChanged.connect(self.change_size_of_tool)
        self.fontComboBox.activated.connect(self.change_font)
        self.bold.clicked.connect(self.change_font)
        self.italic.clicked.connect(self.change_font)
        self.underline.clicked.connect(self.change_font)

        # Init triggers for color buttons
        for n in range(0, 16):
            getattr(self, 'color_btn_%s' % n).clicked.connect(self.quick_change_color)
        self.main_color_btn_1.clicked.connect(self.change_active_color)
        self.main_color_btn_2.clicked.connect(self.change_active_color)
        self.reverse_main_colors_btn.clicked.connect(self.reverse_colors_btn)
        self.restart_main_color_btn.clicked.connect(self.restart_colors_btn)
        self.change_color_btn.clicked.connect(self.openColorDialog)

        # init triggers for layers buttons
        self.add_layer_btn.clicked.connect(self.add_layer)
        self.del_layer_btn.clicked.connect(self.del_layer)
        self.listWidget.itemSelectionChanged.connect(self.layer_selected)

    # History actions

    def add_to_history(self):
        value = self.current_pixmap.copy()
        layer = self.listWidget.selectedItems()[-1]
        id = layer.statusTip()
        self.canvas_history.add([id, value])

    def next_history(self):
        zip_result = self.canvas_history.next()
        if zip_result != 404:
            id, value = zip_result
            self.layers_dict[id] = value.copy()
            self.current_pixmap = self.layers_dict[id]

    def back_history(self):
        zip_result = self.canvas_history.back()
        if zip_result != 404:
            id, value = zip_result
            self.layers_dict[id] = value.copy()
            self.current_pixmap = self.layers_dict[id]

    # Layers actions

    def add_layer(self, priority=None):
        if not self.pixmap.isNull():
            if priority == 'Main':
                pixmap_for_layer = self.pixmap
            else:
                pixmap_for_layer = QPixmap(self.pixmap.width(), self.pixmap.height())
                pixmap_for_layer.fill(QtCore.Qt.transparent)
            layer = QListWidgetItem()
            layer.setCheckState(QtCore.Qt.Checked)
            layer.setIcon(QIcon(pixmap_for_layer))

            count_layers = self.listWidget.count()
            layer.setText(f'Новый слой #{count_layers}')
            layer.setStatusTip(f'layer#{count_layers}')
            layer.setFlags(layer.flags() | QtCore.Qt.ItemIsEditable)

            self.listWidget.addItem(layer)

            if priority == 'Main':
                self.current_pixmap = self.pixmap.copy()
                layer.setSelected(True)
            self.layers_dict[self.listWidget.item(count_layers).statusTip()] = pixmap_for_layer

    def del_layer(self):
        if not self.pixmap.isNull():
            selected_layer = self.listWidget.currentRow()
            self.listWidget.takeItem(selected_layer)

    def show_layers(self, operation=None):
        all_layers_pixmap = QPixmap(self.pixmap.size())
        all_layers_pixmap.fill(QtCore.Qt.transparent)
        qp = QPainter(all_layers_pixmap)
        qp.setCompositionMode(QPainter.CompositionMode_DestinationOver)
        names = []
        for row in range(self.listWidget.count()):
            item = self.listWidget.item(row)
            regex = r"[(]\d*[)]"
            names.append(item.text().split(' (')[0] if re.findall(regex, item.text()) else item.text())
            if names.count(item.text()) > 1:
                item.setText(f'{item.text()} ({names.count(item.text()) - 1})')

            if item.checkState() == QtCore.Qt.Checked:
                if operation:
                    self.layers_dict[item.statusTip()] = getattr(self.layers_dict[item.statusTip()], operation[0])(operation[1])
                    self.current_pixmap = self.layers_dict[item.statusTip()]
                    item.setIcon(QIcon(self.layers_dict[item.statusTip()]))
                qp.drawPixmap(0, 0, self.layers_dict[item.statusTip()])

        # Update all
        self.pixmap = all_layers_pixmap
        self.image.setPixmap(self.pixmap)

    def update_current_layer(self, priority=None):
        if self.listWidget.count() > 0:
            if priority == 'temp':
                self.temped = True
                layer = self.listWidget.selectedItems()[-1]
                self.layers_dict[layer.statusTip()] = self.current_pixmap
                self.current_pixmap = self.temp_pixmap.copy()
            else:
                self.temp_pixmap = self.current_pixmap.copy()
                layer = self.listWidget.selectedItems()[-1]
                layer.setIcon(QIcon(self.current_pixmap))
                self.layers_dict[layer.statusTip()] = self.current_pixmap.copy()
                if priority == 'release':
                    self.add_to_history()

    def layer_selected(self):
        if self.listWidget.currentItem():
            layer = self.layers_dict[self.listWidget.currentItem().statusTip()]
            self.current_pixmap = layer
            self.temp_pixmap = self.current_pixmap.copy()

    # File menu events

    def newFileDialog(self):
        item, ok_pressed = QInputDialog.getItem(
            self, "Создание",
            "Введите размер изображения (weight * height)(МОЖЕТ БЫТЬ ИЗМЕНЁН!)" +
            "\nили выберите из предложенных:",
            self.default_sizes_of_created_image, 3, True)

        try:
            if ok_pressed:
                w, h = [int(elem) for elem in item.split('*')]
                if w <= 20000 and h <= 20000:
                    self.pixmap = QPixmap(w, h)
                    self.pixmap.fill(QColor('#FFFFFF'))
                    self.current_file_name = False
                    self.image.setPixmap(self.pixmap)
                    self.update_image_by_window_size()
                    self.add_layer(priority='Main')
        except ValueError:
            QMessageBox.critical(
                self, "Ошибка", "Неверный формат введённых данных",
                QMessageBox.Ok)

    def openFileNameDialog(self):
        fname, _ = QFileDialog.getOpenFileName(
            self, "Открыть изображение", "", self.file_extensions)

        if fname:
            self.pixmap = QPixmap(fname)
            self.current_file_name = fname
            self.image.setPixmap(self.pixmap)
            self.update_image_by_window_size()
            self.add_layer(priority='Main')

    def saveFileDialog(self):
        if self.current_file_name:
            self.pixmap.save(self.current_file_name)
        else:
            self.save_asFileDialog()

    def save_asFileDialog(self):
        fname, _ = QFileDialog.getSaveFileName(
            self, "Сохранить файл", "", self.file_extensions)
        if fname:
            self.current_file_name = fname
            self.pixmap.save(fname)

    # Image events

    def update_image_by_window_size(self):
        main_image_widget_width = self.width() - self.difference_size[0]
        main_image_widget_height = self.height() - self.difference_size[1]
        image_width, image_height = self.pixmap.width(), self.pixmap.height()

        if image_width > main_image_widget_width or \
                image_height > main_image_widget_height:

            if image_height - main_image_widget_height >= \
                    image_width - main_image_widget_width:

                image_height = main_image_widget_height
                image_width = self.pixmap.width() * image_height // self.pixmap.height()

            elif image_height - main_image_widget_height <= \
                    image_width - main_image_widget_width:

                image_width = main_image_widget_width
                image_height = self.pixmap.height() * image_width // self.pixmap.width()

        self.pixmap = self.pixmap.scaled(image_width, image_height, QtCore.Qt.KeepAspectRatio)
        self.image.resize(image_width, image_height)
        self.image.move((main_image_widget_width - image_width) // 2,
                        (main_image_widget_height - image_height) // 2)
        self.image.setPixmap(self.pixmap)

        self.image_size_label_2.setText(
            f'{self.pixmap.width()} * {self.pixmap.height()}px')

    # to change image

    def flip_gorizontally_image(self):
        self.pixmap = self.pixmap.transformed(QTransform().scale(1, -1))

        self.show_layers(['transformed', QTransform().scale(1, -1)])
        self.image.setPixmap(self.pixmap)
        # self.update_image_by_window_size()

    def flip_vertically_image(self):
        self.pixmap = self.pixmap.transformed(QTransform().scale(-1, 1))

        self.show_layers(['transformed', QTransform().scale(-1, 1)])
        self.image.setPixmap(self.pixmap)
        # self.update_image_by_window_size()

    def turn_image(self, rotate):
        self.pixmap = self.pixmap.transformed(QTransform().rotate(rotate))
        self.show_layers(['transformed', QTransform().rotate(rotate)])
        self.image.setPixmap(self.pixmap)
        # self.update_image_by_window_size()

    def show_info_form(self):
        self.second_form = InfoForm()
        self.second_form.show()

    # Change

    def change_font(self):
        self.font = self.fontComboBox.currentFont()
        self.font.setBold(self.bold.isChecked())
        self.font.setItalic(self.italic.isChecked())
        self.font.setUnderline(self.underline.isChecked())

    def change_tool(self, button):
        self.active_tool = button.objectName()
        self.change_cursor(self.active_tool)
        self.change_comment(self.active_tool)

        # When you change the tool, the temp parts of tools (temp text or alpha border) should be removed
        self.priority = None
        self.current_text = ""
        self.polygon_points = []

        if self.active_tool == self.text.objectName():
            self.change_size_spinBox.setValue(self.text_size)
        else:
            self.change_size_spinBox.setValue(self.tool_size)

    def change_size_of_tool(self):
        if self.active_tool == self.text.objectName():
            self.text_size = self.change_size_spinBox.value()
            self.font.setPointSize(self.text_size)
        else:
            self.tool_size = self.change_size_spinBox.value()

    def change_active_color(self):
        button = self.sender()
        self.active_color = button

    def change_cursor(self, tool_name):
        con = sqlite3.connect('tool_cursors_settings.sqlite')
        cur = con.cursor()
        res = cur.execute(
            """SELECT im, pos_x, pos_y FROM cursors 
            WHERE id = (SELECT cur_id from tools WHERE name = ?)""",
            (tool_name,)).fetchall()
        con.close()

        im_cur, pos_x, pos_y = res[0]
        self.image.setCursor(QCursor(QPixmap(im_cur), pos_x, pos_y))

    def change_comment(self, tool_name):
        with open('tool_comments.csv', 'rt', encoding='UTF-8', newline='') as csv_file:
            self.info_label.setText(list(DictReader(
                csv_file, delimiter=';', quotechar='"'))[0][tool_name])

    # Color buttons events.

    def quick_change_color(self):
        obj_name = self.sender().objectName()
        color = COLORS[int(obj_name[obj_name.rfind("_") + 1:])]
        self.set_background_btn_color(color)

    def set_background_btn_color(self, color, btn=False):
        btn = btn if btn else self.active_color
        btn.setStyleSheet(
            'QPushButton:pressed {background-color: rgb(85, 170, 255);' +
            'border-left: 28px solid rgb(85, 170, 255);border: none;}' +
            'QPushButton{border:1px solid #A0A0A0;' +
            f'background: {color}' + ';}')
        self.get_main_color[btn] = color

    def openColorDialog(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.set_background_btn_color(color.name())
            self.get_main_color[self.active_color] = color.name()

    def reverse_colors_btn(self):
        first_color = self.get_main_color[self.main_color_btn_1]
        second_color = self.get_main_color[self.main_color_btn_2]
        self.set_background_btn_color(second_color, btn=self.main_color_btn_1)
        self.set_background_btn_color(first_color, btn=self.main_color_btn_2)

    def restart_colors_btn(self):
        self.set_background_btn_color(DEFAULT_COLORS[0], btn=self.main_color_btn_1)
        self.set_background_btn_color(DEFAULT_COLORS[1], btn=self.main_color_btn_2)

    # Mouse events.

    def mousePressEvent(self, event):
        self.update_image_by_window_size()
        self.cursor_position_label.setText(
            f'{self.image.mapFromGlobal(QCursor.pos()).x()} * ' +
            f'{self.image.mapFromGlobal(QCursor.pos()).y()}px')

        operation = getattr(self, '%s_mousePressEvent' % self.active_tool)
        if operation:
            operation(event)
            self.update_current_layer(self.priority)

    def mouseMoveEvent(self, event):
        operation = getattr(self, '%s_mouseMoveEvent' % self.active_tool, None)
        if operation:
            operation(event)
            self.update_current_layer(self.priority)

    def mouseReleaseEvent(self, event):
        operation = getattr(self, '%s_mouseReleaseEvent' % self.active_tool, None)
        if operation:
            operation(event)
            if self.active_tool != 'text' or self.active_tool != 'drawPolygon' or self.active_tool != 'select':
                self.update_current_layer('release')

    # Keyboard events.

    def keyPressEvent(self, event):
        if self.active_tool == 'drawPolygon' and self.polygon_points:
            if event.key() == QtCore.Qt.Key_Return:
                qp = QPainter(self.current_pixmap)
                qp.setPen(self.regularly_pen)

                if self.choose_contour_figure_checkBox.checkState() == QtCore.Qt.Checked:
                    qp.setPen(self.regularly_pen)
                else:
                    pen = self.regularly_pen
                    pen.setColor(QColor(self.get_main_color[self.main_color_btn_2]))
                    qp.setPen(pen)
                if self.choose_filling_figure_checkBox.checkState() == QtCore.Qt.Checked:
                    qp.setBrush(QColor(self.get_main_color[self.main_color_btn_2]))

                qp.drawPolygon(*self.polygon_points)

                self.update()
                self.pixmap = self.image.pixmap().copy()
                self.polygon_points = []
                self.priority = None
                self.update_current_layer('release')

        elif self.active_tool == 'text' and self.is_text_can_writed:
            self.text_writeOnScreen(event)
            self.update_current_layer(self.priority)
            self.priority = None

    # Brush events.

    def brush_mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.lastPoint = self.image.mapFromGlobal(QCursor.pos())
            self.brush_mouseMoveEvent(event)

    def brush_mouseMoveEvent(self, event):
        qp = QPainter(self.current_pixmap)
        qp.setPen(QPen(QColor(self.get_main_color[self.active_color]),
                       self.tool_size, QtCore.Qt.SolidLine, QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin))

        qp.drawLine(self.lastPoint, self.image.mapFromGlobal(QCursor.pos()))
        self.lastPoint = self.image.mapFromGlobal(QCursor.pos())
        self.update()

    def brush_mouseReleaseEvent(self, event):
        self.pixmap = self.image.pixmap().copy()
        self.lastPoint = QtCore.QPoint()

    # Pencil events.

    def pencil_mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.lastPoint = self.image.mapFromGlobal(QCursor.pos())
            self.brush_mouseMoveEvent(event)

    def pencil_mouseMoveEvent(self, event):
        qp = QPainter(self.current_pixmap)
        qp.setPen(QPen(QColor(self.get_main_color[self.active_color]),
                       1, QtCore.Qt.SolidLine, QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin))

        qp.drawLine(self.lastPoint, self.image.mapFromGlobal(QCursor.pos()))
        self.lastPoint = self.image.mapFromGlobal(QCursor.pos())
        self.update()

    def pencil_mouseReleaseEvent(self, event):
        self.pixmap = self.image.pixmap().copy()
        self.lastPoint = QtCore.QPoint()

    # Eraser events.

    def eraser_mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.lastPoint = self.image.mapFromGlobal(QCursor.pos())
            self.eraser_mouseMoveEvent(event)

    def eraser_mouseMoveEvent(self, event):
        qp = QPainter(self.current_pixmap)
        if self.current_pixmap.hasAlpha():
            qp.setCompositionMode(QPainter.CompositionMode_Clear)
        qp.setPen(QPen(QColor(255, 255, 255, 255), self.tool_size,
                       QtCore.Qt.SolidLine, QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin))

        qp.drawLine(self.lastPoint, self.image.mapFromGlobal(QCursor.pos()))
        self.lastPoint = self.image.mapFromGlobal(QCursor.pos())
        self.update()

    def eraser_mouseReleaseEvent(self, event):
        self.pixmap = self.image.pixmap().copy()
        self.lastPoint = QtCore.QPoint()
        self.priority = None

    # Pipette events.

    def pipette_mousePressEvent(self, event):
        image = self.pixmap.toImage()
        pixel = image.pixel(self.image.mapFromGlobal(QCursor.pos()))
        color_of_pixel = QColor(pixel).name()
        self.set_background_btn_color(color_of_pixel)

    def pipette_mouseMoveEvent(self, event):
        self.pipette_mousePressEvent(event)

    def pipette_mouseReleaseEvent(self, event):
        self.pipette_mousePressEvent(event)

    # Filling events.

    def filling_mousePressEvent(self, event):
        self.change_cursor('wait')
        qp = QPainter(self.current_pixmap)
        qp.setPen(QPen(QColor(self.get_main_color[self.active_color])))

        im = self.current_pixmap.toImage()
        im_width, im_height = im.width(), im.height()
        im_cords = self.image.mapFromGlobal(QCursor.pos())
        im_x, im_y = im_cords.x(), im_cords.y()

        colored_pix = set()
        pix_queue = set()
        pix_queue.add((im_x, im_y))

        def add_queue_points(x, y):
            for x1, y1 in ((x + 1, y), (x, y + 1), (x - 1, y), (x, y - 1)):
                if 0 <= x1 <= im_width and 0 <= y1 <= im_height and (x1, y1) not in colored_pix:
                    pix_queue.add((x1, y1))
                    colored_pix.add((x1, y1))

        repaint_color = im.pixel(im_x, im_y)
        while pix_queue:
            pix_x, pix_y = pix_queue.pop()
            if im.pixel(pix_x, pix_y) == repaint_color:
                qp.drawPoint(QtCore.QPoint(pix_x, pix_y))
                add_queue_points(pix_x, pix_y)

        self.change_cursor(self.active_tool)
        self.update()
        self.priority = None

    # Text events.

    def text_mousePressEvent(self, event):
        self.firstPoint = self.image.mapFromGlobal(QCursor.pos())
        self.current_text = ""
        self.is_text_can_writed = True

    def text_writeOnScreen(self, event):
        self.priority = 'temp'
        if event.key() == QtCore.Qt.Key_Backspace:
            self.current_text = self.current_text[:-1]
        elif event.key() == QtCore.Qt.Key_Return:
            self.priority = 'release'
            self.is_text_can_writed = False
        else:
            self.current_text += event.text()
        qp = QPainter(self.current_pixmap)
        qp.setPen(QPen(QColor(self.get_main_color[self.active_color])))
        qp.setFont(self.font)
        qp.drawText(self.firstPoint, self.current_text)
        self.update()

    # make form for drawForm_mouseMoveEvents

    def drawForm_mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.image.setCursor(QtCore.Qt.CrossCursor)
            self.firstPoint = self.image.mapFromGlobal(QCursor.pos())
            self.lastPoint = self.image.mapFromGlobal(QCursor.pos()) - self.firstPoint

    def drawForm_mouseMoveEvent(self, event, qp, pen=MAKE_FORM_PEN):
        self.lastPoint = self.image.mapFromGlobal(QCursor.pos()) - self.firstPoint
        qp.setCompositionMode(QPainter.RasterOp_SourceXorDestination)
        qp.setPen(pen)
        qp.pen().setDashOffset(1)

        self.rect_for_draw = QtCore.QRect(self.firstPoint.x(), self.firstPoint.y(),
                                          self.lastPoint.x(), self.lastPoint.y())

        if self.active_tool == 'drawRoundedRect':
            point_1_x, point_1_y = self.firstPoint.x(), self.firstPoint.y()
            point_2_x, point_2_y = self.lastPoint.x(), self.lastPoint.y()
            getattr(qp, self.active_tool)(QtCore.QRect(point_1_x, point_1_y, point_2_x, point_2_y),
                                          10, 10, QtCore.Qt.RelativeSize)
        else:
            if self.active_tool == 'drawPolygon':
                qp.drawPolygon(*self.polygon_points)
            else:
                getattr(qp, self.active_tool)(self.rect_for_draw)
        self.priority = 'temp'

    def drawForm_mouseReleaseEvent(self, event):
        qp = QPainter(self.current_pixmap)
        if self.choose_contour_figure_checkBox.isChecked():
            pen = self.regularly_pen
            pen.setColor(QColor(self.get_main_color[self.main_color_btn_1]))
            qp.setPen(pen)
        else:
            pen = self.regularly_pen
            pen.setColor(QColor(self.get_main_color[self.main_color_btn_2]))
            qp.setPen(pen)
        if self.choose_filling_figure_checkBox.checkState() == QtCore.Qt.Checked:
            qp.setBrush(QColor(self.get_main_color[self.main_color_btn_2]))

        self.rect_for_draw = QtCore.QRect(self.firstPoint.x(), self.firstPoint.y(),
                                          self.lastPoint.x(), self.lastPoint.y())

        if self.active_tool == 'drawRoundedRect':
            getattr(qp, self.active_tool)(self.rect_for_draw, 10, 10)
        else:
            getattr(qp, self.active_tool)(self.rect_for_draw)

        self.image.setPixmap(self.pixmap)
        self.priority = None

    # DrawLine events.

    def drawLine_mousePressEvent(self, event):
        self.drawForm_mousePressEvent(event)
        self.lastPoint = self.image.mapFromGlobal(QCursor.pos())

    def drawLine_mouseMoveEvent(self, event, pen=MAKE_FORM_PEN):
        self.lastPoint = self.image.mapFromGlobal(QCursor.pos())
        qp = QPainter(self.current_pixmap)
        if pen == MAKE_FORM_PEN:
            qp.setCompositionMode(QPainter.RasterOp_SourceXorDestination)
            self.priority = 'temp'
        else:
            self.priority = None
        qp.setPen(pen)
        qp.pen().setDashOffset(1)
        qp.drawLine(self.firstPoint, self.lastPoint)
        self.update()
        self.pixmap = self.image.pixmap().copy()

    def drawLine_mouseReleaseEvent(self, event):
        self.drawLine_mouseMoveEvent(event, self.regularly_pen)

    # DrawCurveLine events.

    def drawCurveLine_mousePressEvent(self, event):
        if self.is_drawed_line_for_curve:
            self.rect_for_draw = QtCore.QRect(self.firstPoint, self.lastPoint)
        else:
            self.drawLine_mousePressEvent(event)

    def drawCurveLine_mouseMoveEvent(self, event):
        if self.is_drawed_line_for_curve:
            self.drawCurveLineAngle(event)
        else:
            self.drawLine_mouseMoveEvent(event)

    def drawCurveLine_mouseReleaseEvent(self, event):
        if self.is_drawed_line_for_curve:
            self.is_drawed_line_for_curve = False
            self.drawCurveLineAngle(event, self.regularly_pen)
        else:
            self.drawLine_mouseMoveEvent(event)
            self.is_drawed_line_for_curve = True
            self.update_current_layer('temp')

    def drawCurveLineAngle(self, event, pen=MAKE_FORM_PEN):
        def calculateAngle(for_last_point=False):
            if for_last_point:
                p1, p2, p3 = self.rect_for_draw.bottomLeft(), self.rect_for_draw.center(), self.lastPoint
            else:
                p1, p2, p3 = self.firstPoint, self.rect_for_draw.center(), self.lastPoint
            a, b, c = sqrt(((p2.x() - p1.x()) ** 2) + ((p2.y() - p1.y()) ** 2)), \
                               sqrt(((p3.x() - p2.x()) ** 2) + ((p3.y() - p2.y()) ** 2)), \
                               sqrt(((p3.x() - p1.x()) ** 2) + ((p3.y() - p1.y()) ** 2))
            angle = round(degrees(acos((a**2 + b**2 - c**2) / (2 * a * b))), 0)
            return angle

        self.lastPoint = self.image.mapFromGlobal(QCursor.pos())
        qp = QPainter(self.current_pixmap)
        if pen == MAKE_FORM_PEN:
            qp.setCompositionMode(QPainter.RasterOp_SourceXorDestination)
            self.priority = 'temp'
        else:
            self.priority = None
        qp.setPen(pen)
        qp.pen().setDashOffset(1)
        startAngle, spanAngle = calculateAngle() * 16, calculateAngle(True) * 16
        qp.drawArc(self.rect_for_draw, startAngle, spanAngle)
        self.update()
        self.pixmap = self.image.pixmap().copy()

    # DrawEllipse events.

    def drawEllipse_mousePressEvent(self, event):
        self.drawForm_mousePressEvent(event)

    def drawEllipse_mouseMoveEvent(self, event):
        # self.image.setPixmap(self.pixmap.copy())
        qp = QPainter(self.current_pixmap)
        self.drawForm_mouseMoveEvent(event, qp)

    def drawEllipse_mouseReleaseEvent(self, event):
        self.drawForm_mouseReleaseEvent(event)

    # DrawRectangle events.

    def drawRect_mousePressEvent(self, event):
        self.drawForm_mousePressEvent(event)

    def drawRect_mouseMoveEvent(self, event):
        # self.image.setPixmap(self.pixmap.copy())
        qp = QPainter(self.current_pixmap)
        self.drawForm_mouseMoveEvent(event, qp)

    def drawRect_mouseReleaseEvent(self, event):
        self.drawForm_mouseReleaseEvent(event)

    # DrawRoundedRectangle events.

    def drawRoundedRect_mousePressEvent(self, event):
        self.drawForm_mousePressEvent(event)

    def drawRoundedRect_mouseMoveEvent(self, event):
        # self.image.setPixmap(self.pixmap.copy())
        qp = QPainter(self.current_pixmap)
        self.drawForm_mouseMoveEvent(event, qp)

    def drawRoundedRect_mouseReleaseEvent(self, event):
        self.drawForm_mouseReleaseEvent(event)

    # drawPolygon events.

    def drawPolygon_mousePressEvent(self, event):
        self.drawForm_mousePressEvent(event)
        self.lastPoint += self.firstPoint
        if getattr(self, 'polygon_points', None):
            self.polygon_points.append(self.lastPoint)
        else:
            self.polygon_points = [self.firstPoint, self.lastPoint]

    def drawPolygon_mouseMoveEvent(self, event):
        self.image.setPixmap(self.pixmap.copy())
        qp = QPainter(self.current_pixmap)
        self.lastPoint = self.image.mapFromGlobal(QCursor.pos())
        self.polygon_points[-1] = self.lastPoint
        self.drawForm_mouseMoveEvent(event, qp)

    def drawPolygon_mouseReleaseEvent(self, event):
        self.drawPolygon_mouseMoveEvent(event)
        self.update_current_layer('temp')

    # Select events

    def select_mousePressEvent(self, event):
        self.drawForm_mousePressEvent(event)

    def select_mouseMoveEvent(self, event):
        qp = QPainter(self.current_pixmap)
        self.active_tool = 'drawRect'
        self.drawForm_mouseMoveEvent(event, qp, SELECTION_PEN)
        self.active_tool = 'select'
        self.priority = 'temp'

    def select_mouseReleaseEvent(self, event):
        self.select_mouseMoveEvent(event)
        self.update_current_layer('temp')

    def clean_selection(self):
        if self.active_tool == 'select':
            qp = QPainter(self.current_pixmap)
            if self.current_pixmap.hasAlpha():
                qp.setCompositionMode(QPainter.CompositionMode_Clear)
            qp.eraseRect(self.rect_for_draw)
            self.priority = None
            self.update_current_layer()

    def crop_image(self):
        if self.active_tool == 'select':
            self.update_current_layer('temp')
            operation = 'copy'
            args = self.rect_for_draw
            self.pixmap = getattr(self.pixmap, operation)(args)
            self.image.setPixmap(self.pixmap)
            self.show_layers([operation, args])
            self.update_image_by_window_size()


class InfoForm(QWidget):
    def __init__(self):
        super().__init__()
        self.setGeometry(300, 150, 300, 350)
        self.setFixedSize(self.width(), self.height())
        self.setWindowIcon(QIcon('icons/main_icon.png'))
        self.setWindowTitle('PyPaint: info')

        self.label_im = QLabel(self)
        self.label_im.setGeometry(20, 20, 260, 260)
        pixmap = QPixmap('icons/main_icon.png')
        pixmap = pixmap.scaled(260, 260)
        self.label_im.setPixmap(pixmap)

        self.plainTextEdit = QTextBrowser(self)
        self.plainTextEdit.setGeometry(90, 290, 260, 50)
        self.plainTextEdit.setText('Версия 1.0')
        self.plainTextEdit.setStyleSheet('border: none; background: #F0F0F0;')

        HTML = ""
        for i in self.plainTextEdit.toPlainText():
            color = "#{:06x}".format(randrange(0, 0xFFFFFF))
            HTML += "<font color='{}' size = {} >{}</font>".format(
                color, randrange(5, 8), i)
        self.plainTextEdit.setHtml(HTML)


def except_hook(cls, exception, traceback):
    sys.__excepthook__(cls, exception, traceback)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    form = MainWindow()
    form.show()
    sys.excepthook = except_hook
    sys.exit(app.exec())
