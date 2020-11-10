from PyQt5.QtWidgets import QApplication
import sys
import inspect
from PyQt5 import QtWidgets, QtCore, QtGui, uic
from PIL import ImageQt, Image, ImageFilter


SELECTION_PEN = QtGui.QPen(QtGui.QColor(0xff, 0xff, 0xff), 1, QtCore.Qt.DashLine)
MAKE_FORM_PEN = QtGui.QPen(QtGui.QColor(0xff, 0xff, 0xff), 1, QtCore.Qt.SolidLine)
CADRE_FORM_PEN = QtGui.QPen(QtGui.QColor(0xff, 0xff, 0xff), 5, QtCore.Qt.SolidLine)


def except_hook(cls, exception, traceback):
    sys.__excepthook__(cls, exception, traceback)


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

    def back(self):
        if self.count - 1 > -1:
            self.count -= 1
            return self.history[self.count]

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


class Paint(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi('MainWindow.ui', self)
        self.set_buttons()
        self.file_extensions = "All Files (*);;JPG (*.jpg);;PNG (*.png)"

        self.firstPoint = QtCore.QPoint()
        self.lastPoint = QtCore.QPoint()
        self.drawing = False
        self.pixmap = QtGui.QPixmap()
        self.temp_pixmap = self.pixmap.copy()
        self.im_true_size = (0, 0)
        self.which_tool = 'drawLine'

        self.fault = QtCore.QPoint(193, 71)

        self.color_for_tool = QtGui.QColor('#000000')
        self.size_of_tool = self.choose_size_of_tool.value()
        self.font = self.fontComboBox.currentFont()
        self.text = 'j'
        self.history = History()

        self.rect_for_draw = QtCore.QRect()

        # init cursors
        self.DrawCursor = QtGui.QCursor(QtGui.QPixmap('cursors/draw.png'), 0, 0)
        self.PipetteCursor = QtGui.QCursor(QtGui.QPixmap('cursors/pipette.png'), 0, 0)

    def set_buttons(self):
        # init triggers for buttons in menu
        self.open_btn.triggered.connect(self.openFileNameDialog)
        self.save_as_btn.triggered.connect(self.saveFileDialog)
        self.create_btn.triggered.connect(self.newFileDialog)
        self.makeForward.triggered.connect(self.next)
        self.makeBack.triggered.connect(self.back)
        self.deleteContent.triggered.connect(self.delete_some_content)
        self.choose_color.clicked.connect(self.openColorDialog)

        self.choose_font_point.valueChanged.connect(self.change_font_point)
        self.choose_size_of_tool.valueChanged.connect(self.change_size_of_tool)
        self.fontComboBox.currentFontChanged.connect(self.change_font)

        self.instruments_group = QtWidgets.QButtonGroup()
        self.instruments_group.addButton(self.drawLine)
        self.instruments_group.addButton(self.drawText)
        self.instruments_group.addButton(self.drawRect)
        self.instruments_group.addButton(self.drawRoundedRect)
        # self.instruments_group.addButton(self.drawPolygon)
        self.instruments_group.addButton(self.drawEllipse)
        self.instruments_group.addButton(self.cadre)
        self.instruments_group.addButton(self.move_btn)
        self.instruments_group.addButton(self.select)
        self.instruments_group.addButton(self.pipette)

        self.instruments_group.buttonClicked.connect(self.change_tool)

    def openFileNameDialog(self):
        options = QtWidgets.QFileDialog.Options()
        options |= QtWidgets.QFileDialog.DontUseNativeDialog
        fileName, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Открыть изображение",
                                                            "",
                                                            self.file_extensions,
                                                            options=options)
        if fileName:
            if fileName[fileName.rfind('.'):] not in self.file_extensions:
                self.showPopupDialog(QtWidgets.QMessageBox.Critical)
            else:
                im = Image.open(fileName)
                self.im_true_size = im.size
                self.pixmap = QtGui.QPixmap(fileName)
                self.main_pix.setPixmap(self.pixmap)
                self.history.add(self.pixmap.copy())

    def openColorDialog(self):
        color = QtWidgets.QColorDialog.getColor()
        if color.isValid():
            self.change_color(color)

    def newFileDialog(self):
        properties, ok = QtWidgets.QInputDialog.getInt(self, 'Ширина:', '')

        if ok:
            self.pixmap = QtGui.QPixmap(properties, properties)
            self.pixmap.fill(QtGui.QColor('#FFFFFF'))
            self.main_pix.setPixmap(self.pixmap)

    def next(self):
        temp_pixmap = self.history.next()
        if temp_pixmap:
            self.pixmap = temp_pixmap.copy()
            self.main_pix.setPixmap(self.pixmap)

    def back(self):
        temp_pixmap = self.history.back()
        if temp_pixmap:
            self.pixmap = temp_pixmap.copy()
            self.main_pix.setPixmap(self.pixmap)

    def change_font(self):
        self.font = self.fontComboBox.currentFont()
        print(self.font)
        self.change_font_point()

    def change_color(self, color):
        self.color_for_tool = QtGui.QColor(color)
        self.choose_color.setStyleSheet(f"background-color: {color.name()};")

    def change_font_point(self):
        self.font.setPointSize(self.choose_font_point.value())
        print(self.choose_font_point.value())

    def change_tool(self, button):
        self.which_tool = button.objectName()

    def change_size_of_tool(self):
        self.size_of_tool = self.choose_size_of_tool.value()

    def regulary_pen(self):
        return QtGui.QPen(self.color_for_tool, self.size_of_tool,
                          QtCore.Qt.SolidLine, QtCore.Qt.SquareCap, QtCore.Qt.MiterJoin)

    def mousePressEvent(self, event):
        if not self.pixmap.isNull():
            operation = getattr(self, '%s_mousePressEvent' % self.which_tool)
            if operation:
                operation(event)

    def mouseMoveEvent(self, event):
        if not self.pixmap.isNull():
            operation = getattr(self, '%s_mouseMoveEvent' % self.which_tool, None)
            if operation:
                operation(event)

    def mouseReleaseEvent(self, event):
        if not self.pixmap.isNull():
            operation = getattr(self, '%s_mouseReleaseEvent' % self.which_tool, None)
            if operation:
                operation(event)

    # drawLine

    def drawLine_mousePressEvent(self, event):
        if not self.pixmap.isNull():
            if event.button() == QtCore.Qt.LeftButton:
                self.main_pix.setCursor(self.DrawCursor)
                self.lastPoint = event.pos() - self.fault
                self.drawLine_mouseMoveEvent(event)

    def drawLine_mouseMoveEvent(self, event):
        qp = QtGui.QPainter(self.main_pix.pixmap())
        qp.setPen(QtGui.QPen(self.color_for_tool, self.size_of_tool, QtCore.Qt.SolidLine))
        qp.drawLine(self.lastPoint, event.pos() - self.fault)
        self.lastPoint = event.pos() - self.fault
        self.update()

    def drawLine_mouseReleaseEvent(self, event):
        self.pixmap = self.main_pix.pixmap().copy()
        self.history.add(self.pixmap.copy())
        self.lastPoint = QtCore.QPoint()

    # make form for drawForm_mouseMoveEvents

    def drawForm_mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.main_pix.setCursor(QtCore.Qt.CrossCursor)
            self.firstPoint = event.pos() - self.fault
            self.lastPoint = event.pos() - self.fault - self.firstPoint

    def drawForm_mouseMoveEvent(self, event, qp, pen=MAKE_FORM_PEN):
        self.lastPoint = event.pos() - self.fault - self.firstPoint
        qp.setCompositionMode(QtGui.QPainter.RasterOp_SourceXorDestination)
        qp.setPen(pen)
        qp.pen().setDashOffset(1)
        self.rect_for_draw = QtCore.QRect(self.firstPoint.x(), self.firstPoint.y(),
                                          self.lastPoint.x(), self.lastPoint.y())
        if self.which_tool == 'drawRoundedRect':
            getattr(qp, self.which_tool)(self.rect_for_draw, 10, 10, QtCore.Qt.RelativeSize)
        else:
            getattr(qp, self.which_tool)(self.rect_for_draw)
        self.update()

    def drawForm_mouseReleaseEvent(self, event):
        qp = QtGui.QPainter(self.pixmap)
        qp.setPen(self.regulary_pen())
        self.rect_for_draw = QtCore.QRect(self.firstPoint.x(), self.firstPoint.y(),
                                          self.lastPoint.x(), self.lastPoint.y())
        if self.which_tool == 'drawRoundedRect':
            getattr(qp, self.which_tool)(self.rect_for_draw, 10, 10)
        else:
            getattr(qp, self.which_tool)(self.rect_for_draw)
        self.update()
        self.main_pix.setPixmap(self.pixmap)
        self.history.add(self.pixmap.copy())

    # drawRect

    def drawRect_mousePressEvent(self, event):
        self.drawForm_mousePressEvent(event)

    def drawRect_mouseMoveEvent(self, event):
        self.main_pix.setPixmap(self.pixmap.copy())
        qp = QtGui.QPainter(self.main_pix.pixmap())
        self.drawForm_mouseMoveEvent(event, qp)

    def drawRect_mouseReleaseEvent(self, event):
        self.drawForm_mouseReleaseEvent(event)

    # drawEllipse

    def drawEllipse_mousePressEvent(self, event):
        self.drawForm_mousePressEvent(event)

    def drawEllipse_mouseMoveEvent(self, event):
        self.main_pix.setPixmap(self.pixmap.copy())
        qp = QtGui.QPainter(self.main_pix.pixmap())
        self.drawForm_mouseMoveEvent(event, qp)

    def drawEllipse_mouseReleaseEvent(self, event):
        self.drawForm_mouseReleaseEvent(event)

    # drawRoundedRect

    def drawRoundedRect_mousePressEvent(self, event):
        self.drawForm_mousePressEvent(event)

    def drawRoundedRect_mouseMoveEvent(self, event):
        self.main_pix.setPixmap(self.pixmap.copy())
        qp = QtGui.QPainter(self.main_pix.pixmap())
        self.drawForm_mouseMoveEvent(event, qp)

    def drawRoundedRect_mouseReleaseEvent(self, event):
        self.drawForm_mouseReleaseEvent(event)

    # drawPolygon

    def drawPolygon_mousePressEvent(self, event):
        if event.buttons() == [QtCore.Qt.LeftButton + QtCore.Qt.LeftButton]:
            print('2 click')
        self.lastPoint = event.pos() - self.fault
        if getattr(self, 'polygon_points', None):
            self.polygon_points.append(self.lastPoint)
        else:
            self.firstPoint = event.pos() - self.fault
            self.polygon_points = [self.firstPoint, self.lastPoint]

    def drawPolygon_mouseMoveEvent(self, event):
        self.main_pix.setPixmap(self.pixmap.copy())
        qp = QtGui.QPainter(self.main_pix.pixmap())
        self.lastPoint = event.pos() - self.fault
        self.polygon_points[-1] = self.lastPoint
        qp.setCompositionMode(QtGui.QPainter.RasterOp_SourceXorDestination)
        qp.setPen(MAKE_FORM_PEN)
        qp.pen().setDashOffset(1)
        qp.drawPolygon(*self.polygon_points)
        self.update()

    # pipette

    def pipette_mousePressEvent(self, event):
        self.main_pix.setCursor(self.PipetteCursor)
        image = self.pixmap.toImage()
        pixel = image.pixel(event.pos() - self.fault)
        color_of_pixel = QtGui.QColor(pixel)
        self.change_color(color_of_pixel)

    def pipette_mouseMoveEvent(self, event):
        self.pipette_mousePressEvent(event)

    def cadre_mousePressEvent(self, event):
        self.drawForm_mousePressEvent(event)

    def cadre_mouseMoveEvent(self, event):
        self.which_tool = 'drawRect'
        self.main_pix.setPixmap(self.pixmap.copy())
        qp = QtGui.QPainter(self.main_pix.pixmap())
        self.drawForm_mouseMoveEvent(event, qp, CADRE_FORM_PEN)
        # draw crosshair at the center of rect
        qp.setPen(CADRE_FORM_PEN)
        shift_crosshair_x = QtCore.QPoint(10, 0)
        shift_crosshair_y = QtCore.QPoint(0, 10)
        if abs(self.rect_for_draw.width()) > 25 and abs(self.rect_for_draw.height()) > 25:
            qp.drawLine(self.rect_for_draw.center() - shift_crosshair_x,
                        self.rect_for_draw.center() + shift_crosshair_x)
            qp.drawLine(self.rect_for_draw.center() - shift_crosshair_y,
                        self.rect_for_draw.center() + shift_crosshair_y)
        self.update()
        self.which_tool = 'cadre'

    def cadre_mouseReleaseEvent(self, event):
        self.pixmap = self.pixmap.copy(self.rect_for_draw)
        self.main_pix.setPixmap(self.pixmap)
        self.history.add(self.pixmap.copy())

    def select_mousePressEvent(self, event):
        self.drawForm_mousePressEvent(event)

    def select_mouseMoveEvent(self, event):
        self.which_tool = 'drawRect'
        self.main_pix.setPixmap(self.pixmap.copy())
        qp = QtGui.QPainter(self.main_pix.pixmap())
        self.drawForm_mouseMoveEvent(event, qp, SELECTION_PEN)
        self.which_tool = 'select'

    # drawText

    def drawText_mousePressEvent(self, event):
        if self.text:
            self.pixmap = self.main_pix.pixmap()
        else:
            self.drawForm_mousePressEvent(event)
        self.text = ""

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
            qp = QtGui.QPainter(self.main_pix.pixmap())
            qp.setPen(QtGui.QPen(self.color_for_tool))
            qp.setFont(self.font)
            qp.drawText(self.firstPoint, self.text)
            self.update()
        elif self.which_tool == 'drawPolygon':
            if event.key() == QtCore.Qt.Key_Return:
                qp = QtGui.QPainter(self.main_pix.pixmap())
                qp.setPen(self.regulary_pen())
                qp.drawPolygon(*self.polygon_points)
                self.update()
                self.pixmap = self.main_pix.pixmap().copy()
                self.polygon_points = []
                self.history.add(self.pixmap.copy())

    def delete_some_content(self):
        if self.which_tool == 'select':
            qp = QtGui.QPainter(self.pixmap)
            if self.pixmap.hasAlpha():
                qp.setCompositionMode(QtGui.QPainter.CompositionMode_Clear)
            qp.eraseRect(self.rect_for_draw)
            self.update()
            self.main_pix.setPixmap(self.pixmap)
            self.history.add(self.pixmap.copy())

    def saveFileDialog(self):
        options = QtWidgets.QFileDialog.Options()
        options |= QtWidgets.QFileDialog.DontUseNativeDialog
        fileName, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Сохранить файл",
                                                            "",
                                                            self.file_extensions,
                                                            options=options)
        if fileName:
            self.pixmap.save(fileName)

    def showPopupDialog(self, icon):
        message = QtWidgets.QMessageBox()
        message.setWindowTitle('Ошибка!')
        message.setText('Неверный формат файла.')
        message.setIcon(icon)

        x = message.exec_()


if __name__ == '__main__':
    print(type(inspect.signature(ImageFilter.UnsharpMask)))
    app = QApplication(sys.argv)
    ex = Paint()
    ex.show()
    sys.excepthook = except_hook
    sys.exit(app.exec())
