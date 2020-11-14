import sys
from random import randrange

from PyQt5.QtGui import *
from PyQt5 import QtCore
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget
from PyQt5.QtWidgets import QButtonGroup, QLabel, QTextBrowser
from PyQt5.QtWidgets import QInputDialog, QFileDialog, QColorDialog, QMessageBox

from PyQt5 import uic

SELECTION_PEN = QPen(QColor(0xff, 0xff, 0xff), 1, QtCore.Qt.DashLine)
MAKE_FORM_PEN = QPen(QColor(0xff, 0xff, 0xff), 1, QtCore.Qt.SolidLine)
CADRE_FORM_PEN = QPen(QColor(0xff, 0xff, 0xff), 5, QtCore.Qt.SolidLine)

COLORS = ['#000000', '#880016', '#ED1B24', '#FF7F26',
          '#FEF200', '#21B24D', '#00A3E8', '#3F47CC',
          '#FFFFFF', '#C3C3C3', '#B97A57', '#FFC90D',
          '#EFE4AE', '#B5E51D', '#C7BFE6', '#A349A3']

DEFAULT_COLORS = ['#000000', '#FFFFFF']


class MainWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        uic.loadUi('MainWindow.ui', self)
        self.setWindowTitle('PyPaint')
        self.setWindowIcon(QIcon('icons/main_icon.png'))

        self.tools_group = QButtonGroup(self)
        self.connecting_buttons()

        # Tools settings
        self.active_color = self.main_color_btn_1
        self.get_main_color = \
            {self.main_color_btn_1: DEFAULT_COLORS[0],
             self.main_color_btn_2: DEFAULT_COLORS[1]}
        self.font = QFont(self.fontComboBox.currentText())
        self.text_size = 12

        self.tool_size = self.change_size_spinBox.value()
        self.active_tool = None
        self.brush.click()

        self.file_extensions = "All Files (*.png *.jpg);;JPG (*.jpg);;PNG (*.png)"
        self.default_sizes_of_created_image = \
            [f'{lg} * {lg * 3 // 4}' for lg in range(400, 1200, 200)]
        self.difference_size = \
            (self.width() - self.image.width(),
             self.height() - self.image.height())

        # Init default image
        self.pixmap = QPixmap(800, 600)
        self.pixmap.fill(QColor('#FFFFFF'))
        self.temp_pixmap = self.pixmap.copy()
        self.current_file_name = False
        self.image.setPixmap(self.pixmap)
        self.update_image_by_window_size()

        self.lastPoint = QtCore.QPoint()  # прошлая точка
        self.firstPoint = QtCore.QPoint()  # первая точка

        self.DrawCursor = QCursor(QPixmap('cursors/draw.png'), 0, 0)
        self.PipetteCursor = QCursor(QPixmap('cursors/pipette.png'), 0, 0)

        self.rect_for_draw = QtCore.QRect()

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
        # self.pushButton.clicked.connect(self.press_button)
        # self.crop_image_btn.clicked.connect(self.press_button)
        # self.cancel_selection_btn.clicked.connect(self.press_button)

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
        self.tools_group.addButton(self.drawArbitraryFigure)
        self.tools_group.buttonClicked.connect(self.change_tool)
        # Init triggers for widgets in tool_settings_frame
        self.change_size_spinBox.valueChanged.connect(self.change_size_of_tool)
        self.fontComboBox.activated.connect(self.change_font)
        self.bold.clicked.connect(self.change_font)
        self.italic.clicked.connect(self.change_font)
        self.underline.clicked.connect(self.change_font)

        # Init triggers for color buttons
        for n in range(0, 16):
            getattr(self, 'color_btn_%s' % n).clicked.connect(self.change_color)
        self.main_color_btn_1.clicked.connect(self.change_active_color)
        self.main_color_btn_2.clicked.connect(self.change_active_color)
        self.reverse_main_colors_btn.clicked.connect(self.reverse_colors_btn)
        self.restart_main_color_btn.clicked.connect(self.restart_colors_btn)
        self.change_color_btn.clicked.connect(self.openColorDialog)

    # File menu events

    def newFileDialog(self):
        item, ok_pressed = QInputDialog.getItem(
            self, "Создание",
            "Введите размер изображения (weight * height)" +
            "\nили выберите из предложенных:",
            self.default_sizes_of_created_image, 3, True)

        try:
            if ok_pressed:
                self.pixmap = QPixmap(*map(int, item.split('*')))
                self.pixmap.fill(QColor('#FFFFFF'))
                self.current_file_name = False
                self.image.setPixmap(self.pixmap)
                self.update_image_by_window_size()
        except ValueError:
            QMessageBox.critical(
                self, "Ошибка", "Неверный формат введённых данных",
                QMessageBox.Ok)

    def openFileNameDialog(self):
        fname, _ = QFileDialog.getOpenFileName(
            self, "Открыть изображение", "", self.file_extensions)

        if fname:
            self.pixmap = QtGui.QPixmap(fname)
            self.current_file_name = fname
            self.image.setPixmap(self.pixmap)
            self.update_image_by_window_size()

    def saveFileDialog(self):
        if self.currect_file_name:
            self.pixmap.save(self.currect_file_name)
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

    # To change image

    def flip_gorizontally_image(self):
        self.pixmap = self.pixmap.transformed(QTransform().scale(1, -1))
        self.image.setPixmap(self.pixmap)
        self.update_image_by_window_size()

    def flip_vertically_image(self):
        self.pixmap = self.pixmap.transformed(QTransform().scale(-1, 1))
        self.image.setPixmap(self.pixmap)
        self.update_image_by_window_size()

    def turn_image(self, rotate):
        self.pixmap = self.pixmap.transformed(QTransform().rotate(rotate))
        self.image.setPixmap(self.pixmap)
        self.update_image_by_window_size()

    # Show form

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

    # Color buttons events.

    def change_active_color(self):
        self.active_color = self.sender()

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

    def change_color(self):
        obj_name = self.sender().objectName()
        color = COLORS[int(obj_name[obj_name.rfind("_") + 1:])]
        self.set_background_btn_color(color)

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
        self.image_size_label_2.setText(f'{self.pixmap.width()} * {self.pixmap.height()}px')

        operation = getattr(self, '%s_mousePressEvent' % self.active_tool)
        if operation:
            operation(event)

    def mouseMoveEvent(self, event):
        operation = getattr(self, '%s_mouseMoveEvent' % self.active_tool, None)
        if operation:
            operation(event)

    def mouseReleaseEvent(self, event):
        operation = getattr(self, '%s_mouseReleaseEvent' % self.active_tool, None)
        if operation:
            operation(event)

    # Keyboard events.

    def keyPressEvent(self, event):
        if self.which_tool == 'drawText':
            if event.key() == QtCore.Qt.Key_Backspace:
                self.text = self.text[:-1]
            elif event.key() == QtCore.Qt.Key_Enter:
                print('Enter')
                self.text += '\n'
            else:
                self.text += event.text()
            self.main_pix.setPixmap(self.pixmap)
            qp = QPainter(self.main_pix.pixmap())
            qp.setPen(QPen(self.color_for_tool))
            qp.setFont(self.font)
            qp.drawText(self.firstPoint, self.text)
            self.update()
        elif self.which_tool == 'drawPolygon':
            if event.key() == QtCore.Qt.Key_Return:
                qp = QPainter(self.main_pix.pixmap())
                qp.setPen(self.regulary_pen())
                qp.drawPolygon(*self.polygon_points)
                self.update()
                self.pixmap = self.main_pix.pixmap().copy()
                self.polygon_points = []
                self.history.add(self.pixmap.copy())

    # Brush events.

    def brush_mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.image.setCursor(self.DrawCursor)
            self.lastPoint = self.image.mapFromGlobal(QCursor.pos())
            self.brush_mouseMoveEvent(event)

    def brush_mouseMoveEvent(self, event):
        qp = QPainter(self.image.pixmap())
        qp.setPen(QPen(QColor(self.get_main_color[self.active_color]), self.tool_size,
                       QtCore.Qt.SolidLine, QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin))

        qp.drawLine(self.lastPoint, self.image.mapFromGlobal(QCursor.pos()))
        self.lastPoint = self.image.mapFromGlobal(QCursor.pos())
        self.update()

    def brush_mouseReleaseEvent(self, event):
        self.pixmap = self.image.pixmap().copy()
        self.lastPoint = QtCore.QPoint()

    # Pencil events.

    def pencil_mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.image.setCursor(self.DrawCursor)
            self.lastPoint = self.image.mapFromGlobal(QCursor.pos())
            self.brush_mouseMoveEvent(event)

    def pencil_mouseMoveEvent(self, event):
        qp = QPainter(self.image.pixmap())
        qp.setPen(QPen(QColor(self.get_main_color[self.active_color]), 1,
                       QtCore.Qt.SolidLine, QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin))

        qp.drawLine(self.lastPoint, self.image.mapFromGlobal(QCursor.pos()))
        self.lastPoint = self.image.mapFromGlobal(QCursor.pos())
        self.update()

    def pencil_mouseReleaseEvent(self, event):
        self.pixmap = self.image.pixmap().copy()
        self.lastPoint = QtCore.QPoint()

    # Eraser events.

    def eraser_mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.image.setCursor(self.DrawCursor)
            self.lastPoint = self.image.mapFromGlobal(QCursor.pos())
            self.eraser_mouseMoveEvent(event)

    def eraser_mouseMoveEvent(self, event):
        qp = QPainter(self.image.pixmap())
        qp.setPen(QPen(QColor(255, 255, 255, 255), self.tool_size,
                       QtCore.Qt.SolidLine, QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin))

        qp.drawLine(self.lastPoint, self.image.mapFromGlobal(QCursor.pos()))
        self.lastPoint = self.image.mapFromGlobal(QCursor.pos())
        self.update()

    def eraser_mouseReleaseEvent(self, event):
        self.pixmap = self.image.pixmap().copy()
        self.lastPoint = QtCore.QPoint()

    # Pipette events.

    def pipette_mousePressEvent(self, event):
        self.image.setCursor(self.PipetteCursor)
        image = self.pixmap.toImage()
        pixel = image.pixel(self.image.mapFromGlobal(QCursor.pos()))
        color_of_pixel = QColor(pixel).name()
        self.set_background_btn_color(color_of_pixel)

    def pipette_mouseMoveEvent(self, event):
        self.image.setCursor(self.DrawCursor)
        self.pipette_mousePressEvent(event)

    def pipette_mouseReleaseEvent(self, event):
        self.pipette_mousePressEvent(event)

    # Filling events.

    def filling_mousePressEvent(self, event):
        qp = QPainter(self.image.pixmap())
        qp.setPen(QPen(QColor(self.get_main_color[self.active_color])))

        im = self.pixmap.toImage()
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

        self.update()
        self.filling_mouseMoveEvent(event)

    def filling_mouseMoveEvent(self, event):
        self.pixmap = self.image.pixmap().copy()

    def filling_mouseReleaseEvent(self, event):
        pass

    # Text events.

    def text_mousePressEvent(self, event):
        pass

    def text_mouseMoveEvent(self, event):
        pass

    def text_mouseReleaseEvent(self, event):
        pass

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
            getattr(qp, self.active_tool)(self.rect_for_draw, 10, 10, QtCore.Qt.RelativeSize)
        else:
            getattr(qp, self.active_tool)(self.rect_for_draw)
        self.update()

    def drawForm_mouseReleaseEvent(self, event):
        qp = QPainter(self.pixmap)
        qp.setPen(self.regulary_pen())
        self.rect_for_draw = QtCore.QRect(self.firstPoint.x(), self.firstPoint.y(),
                                          self.lastPoint.x(), self.lastPoint.y())
        if self.active_tool == 'drawRoundedRect':
            getattr(qp, self.active_tool)(self.rect_for_draw, 10, 10)
        else:
            getattr(qp, self.active_tool)(self.rect_for_draw)

        self.update()
        self.image.setPixmap(self.pixmap)

    # DrawLine events.

    def drawLine_mousePressEvent(self, event):
        pass

    def drawLine_mouseMoveEvent(self, event):
        pass

    def drawLine_mouseReleaseEvent(self, event):
        pass

    # DrawCurveLine events.

    def drawCurveLine_mousePressEvent(self, event):
        pass

    def drawCurveLine_mouseMoveEvent(self, event):
        pass

    def drawCurveLine_mouseReleaseEvent(self, event):
        pass

    # DrawEllipse events.

    def drawEllipse_mousePressEvent(self, event):
        self.drawForm_mousePressEvent(event)

    def drawEllipse_mouseMoveEvent(self, event):
        self.image.setPixmap(self.pixmap.copy())
        qp = QPainter(self.image.pixmap())
        self.drawForm_mouseMoveEvent(event, qp)

    def drawEllipse_mouseReleaseEvent(self, event):
        self.drawForm_mouseReleaseEvent(event)

    # DrawRectangle events.

    def drawRect_mousePressEvent(self, event):
        self.drawForm_mousePressEvent(event)

    def drawRect_mouseMoveEvent(self, event):
        self.image.setPixmap(self.pixmap.copy())
        qp = QPainter(self.image.pixmap())
        self.drawForm_mouseMoveEvent(event, qp)

    def drawRect_mouseReleaseEvent(self, event):
        self.drawForm_mouseReleaseEvent(event)

    # DrawRoundedRectangle events.

    def drawRoundedRect_mousePressEvent(self, event):
        self.drawForm_mousePressEvent(event)

    def drawRoundedRect_mouseMoveEvent(self, event):
        self.image.setPixmap(self.pixmap.copy())
        qp = QPainter(self.image.pixmap())
        self.drawForm_mouseMoveEvent(event, qp)

    def drawRoundedRect_mouseReleaseEvent(self, event):
        self.drawForm_mouseReleaseEvent(event)

    # DrawArbitraryFigure events.

    def drawArbitraryFigure_mousePressEvent(self, event):
        pass

    def drawArbitraryFigure_mouseMoveEvent(self, event):
        pass

    def drawArbitraryFigure_mouseReleaseEvent(self, event):
        pass

    def regulary_pen(self):
        return QPen(
            QColor(self.get_main_color[self.active_color]), self.tool_size,
            QtCore.Qt.SolidLine, QtCore.Qt.SquareCap, QtCore.Qt.MiterJoin)


class InfoForm(QWidget):
    def __init__(self):
        super().__init__()
        self.setGeometry(300, 150, 300, 350)
        self.setFixedSize(self.width(), self.height())
        self.setWindowTitle('PyPaint: info')

        self.label_im = QLabel(self)
        self.label_im.setGeometry(20, 20, 260, 260)
        pixmap = QPixmap('icons/main_icon.png')
        pixmap = pixmap.scaled(260, 260)
        self.label_im.setPixmap(pixmap)

        self.plainTextEdit = QTextBrowser(self)
        self.plainTextEdit.setGeometry(20 * 3, 290, 260, 50)
        self.plainTextEdit.setText('     Версия 1.0')
        self.plainTextEdit.setStyleSheet('border: none; background: #F0F0F0;')

        HTML = ""
        for i in self.plainTextEdit.toPlainText():
            color = "#{:06x}".format(randrange(0, 0xFFFFFF))
            HTML += "<font color='{}' size = {} >{}</font>".format(color, randrange(5, 8), i)
        self.plainTextEdit.setHtml(HTML)


def except_hook(cls, exception, traceback):
    sys.__excepthook__(cls, exception, traceback)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    form = MainWindow()
    form.show()
    sys.excepthook = except_hook
    sys.exit(app.exec())
