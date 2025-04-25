from aqt.qt import *
from aqt.editor import Editor
from aqt import gui_hooks, mw
from aqt.utils import showInfo
import re
import os
import shutil
import time
import random

class DrawingArea(QLabel):
    def __init__(self, pixmap, parent=None):
        super().__init__(parent)
        self.setPixmap(pixmap)
        self.original_pixmap = pixmap.copy()
        self.rectangle_mode = False
        self.start_point = QPoint()
        self.current_rect = None
        self.rectangles = []
        self.texts = []
        self.text_position = "top"
        self.edited_pixmap = pixmap.copy()
        self.scale_factor = 1.0
        self.original_size = pixmap.size()
        self.timestamp = str(int(time.time()))
        self.setMouseTracking(True)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.rectangle_mode:
            self.start_point = event.pos()
            self.current_rect = QRect(self.start_point, QSize(0, 0))
            self.update_with_rectangles()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton and self.rectangle_mode:
            self.current_rect = QRect(self.start_point, event.pos()).normalized()
            self.update_with_rectangles()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.rectangle_mode and self.current_rect:
            self.current_rect = self.current_rect.normalized()
            if self.current_rect.width() >= 2 and self.current_rect.height() >= 2:
                self.rectangles.append(self.current_rect)
                text, ok = QInputDialog.getText(self, "Texto do Retângulo", "Digite o texto para este retângulo:")
                if ok and text.strip():
                    self.texts.append(text.strip())
                else:
                    self.texts.append(f"Texto {len(self.rectangles)}")
            self.current_rect = None
            self.update_with_rectangles()

    def update_with_rectangles(self):
        pixmap = self.edited_pixmap.copy()
        painter = QPainter(pixmap)
        yellow_solid = QColor(255, 255, 0, 255)
        for rect in self.rectangles:
            painter.fillRect(rect, yellow_solid)
            painter.setPen(QPen(Qt.GlobalColor.black, 2))
            painter.drawRect(rect)
        if self.rectangle_mode and self.current_rect:
            painter.fillRect(self.current_rect, yellow_solid)
            painter.setPen(QPen(Qt.GlobalColor.black, 2))
            painter.drawRect(self.current_rect)
        painter.end()
        self.setPixmap(pixmap)

def generate_html(img_path, pixmap, rectangles, output_dir, scale_factor, timestamp, card_option="single", texts=None, text_position="top"):
    img_filename = os.path.basename(img_path)
    full_path = os.path.join(output_dir, img_filename)
    if not os.path.exists(full_path):
        raise FileNotFoundError(f"Image file not found: {full_path}")
    orig_width = pixmap.width()
    orig_height = pixmap.height()
    texts = texts or []
    
    shuffled_texts = texts.copy()
    random.shuffle(shuffled_texts)
    
    container_style = "position:relative;"
    text_container_style = ""
    if text_position == "top":
        container_style += "display:flex; flex-direction:column; align-items:center;"
        text_container_style = "display:flex; flex-wrap:wrap; gap:10px; margin-bottom:10px;"
    elif text_position == "bottom":
        container_style += "display:flex; flex-direction:column; align-items:center;"
        text_container_style = "display:flex; flex-wrap:wrap; gap:10px; margin-top:10px;"
    elif text_position == "left":
        container_style += "display:flex; flex-direction:row; align-items:flex-start;"
        text_container_style = "display:flex; flex-direction:column; gap:10px; margin-right:10px;"
    elif text_position == "right":
        container_style += "display:flex; flex-direction:row; align-items:flex-start;"
        text_container_style = "display:flex; flex-direction:column; gap:10px; margin-left:10px;"
    
    css = """
.anki-container { max-width:100%; min-height:100px; }
.anki-text-container { background-color:#e0e0e0; padding:5px; border:1px solid #ccc; min-height:30px; }
.anki-text-container.drop-target { background-color:#d0d0d0; border:1px dashed #000; }
.anki-container.drop-target { background-color:rgba(200, 200, 200, 0.2); border:1px dashed #000; }
.anki-text { padding:5px 10px; background-color:#f0f0f0; border:1px solid #000; cursor:move; user-select:none; z-index:20; position:static; }
.anki-text.dragging { opacity:0.5; }
.anki-text.correct { background-color:#00ff00; }
.anki-text.incorrect { background-color:#ff0000; }
.anki-text.free { position:absolute; }
.anki-image-container { position:relative; display:inline-block; max-width:100%; }
.anki-image-container img { max-width:100%; width:100%; display:block; }
.anki-rect, .anki-rect-multi { position:absolute; background-color:yellow; border:2px solid black; cursor:pointer; display:block; }
.anki-rect:hover, .anki-rect-multi:hover { display:none; }
.anki-rect.drop-target, .anki-rect-multi.drop-target { background-color:rgba(0, 255, 0, 0.3); border:2px dashed green; }
.anki-controls { margin-top:10px; }
.anki-controls button { padding:5px 10px; cursor:pointer; margin-right:5px; }
"""
    
    if card_option == "single":
        rects_html = ""
        for i, rect in enumerate(rectangles):
            left_percent = (rect.left() / orig_width) * 100
            top_percent = (rect.top() / orig_height) * 100
            width_percent = (rect.width() / orig_width) * 100
            height_percent = (rect.height() / orig_height) * 100
            rects_html += f"""
            <div class="anki-rect" id="rect{i}" data-correct-text="{texts[i] if i < len(texts) else ''}"
                 style="left:{left_percent}%;top:{top_percent}%;width:{width_percent}%;height:{height_percent}%;z-index:10;"
                 draggable="false">
            </div>"""
            
        texts_html = "".join([f'<div class="anki-text" id="text{i}" draggable="true">{text}</div>' for i, text in enumerate(shuffled_texts)])
        
        return [f"""
<div class="anki-container" style="{container_style}">
    <div class="anki-text-container" style="{text_container_style}">{texts_html}</div>
    <div class="anki-image-container">
        <img src="{img_filename}" style="z-index:1;">
        {rects_html}
    </div>
    <div class="anki-controls">
        <button id="showButton_{timestamp}">👁️‍🗨️ Mostrar</button>
        <button id="hideButton_{timestamp}">👁️ Ocultar</button>
    </div>
</div>
<style>{css}</style>
"""]
    else:
        cards_html = []
        for i, rect in enumerate(rectangles):
            left_percent = (rect.left() / orig_width) * 100
            top_percent = (rect.top() / orig_height) * 100
            width_percent = (rect.width() / orig_width) * 100
            height_percent = (rect.height() / orig_height) * 100
            
            single_card_texts = texts.copy()
            random.shuffle(single_card_texts)
            texts_html = "".join([f'<div class="anki-text" id="text{j}" draggable="true">{text}</div>' for j, text in enumerate(single_card_texts)])
            
            cards_html.append(f"""
<div class="anki-multiple-card" id="card{i}" style="{container_style}">
    <div class="anki-text-container" style="{text_container_style}">{texts_html}</div>
    <div style="position:relative; display:inline-block; max-width:100%;">
        <img src="{img_filename}" style="max-width:100%; width:100%; z-index:1;">
        <div class="anki-rect-multi" id="rect{i}" data-correct-text="{texts[i] if i < len(texts) else ''}"
             style="position:absolute; left:{left_percent}%; top:{top_percent}%; 
                    width:{width_percent}%; height:{height_percent}%; z-index:10;"
             draggable="false">
        </div>
    </div>
    <div style="margin-top:10px;">
        <button id="showBtn{i}_{timestamp}">👁️‍🗨️ Mostrar</button>
        <button id="hideBtn{i}_{timestamp}">👁️ Ocultar</button>
    </div>
</div>
<style>{css}</style>
""")
        return cards_html

def show_image_dialog(self):
    fields = self.note.keys()
    img_field = None
    img_path = None
    for field in fields:
        content = self.note[field]
        img_pattern = r'<img[^>]+src=["\'](.*?)["\']'
        match = re.search(img_pattern, content)
        if match:
            img_field = field
            img_path = match.group(1).split('?')[0]
            break
    
    if not img_field:
        showInfo("Nenhum campo com imagem encontrado!")
        return
        
    collection = self.note.col
    media_dir = collection.media.dir()
    full_path = os.path.join(media_dir, img_path)
    
    if not os.path.exists(full_path):
        showInfo(f"Imagem não encontrada: {full_path}")
        return
        
    backup_path = full_path + ".backup"
    if not os.path.exists(backup_path):
        shutil.copy(full_path, backup_path)
        
    original_filename = f"{os.path.splitext(os.path.basename(img_path))[0]}_original.png"
    original_path = os.path.join(media_dir, original_filename)
    if not os.path.exists(original_path):
        shutil.copy(full_path, original_path)
        
    dialog = QDialog(self.widget)
    dialog.setWindowTitle("Imagem do Campo")
    layout = QVBoxLayout()
    
    pixmap = QPixmap(full_path)
    if pixmap.isNull():
        showInfo("Erro ao carregar a imagem!")
        dialog.close()
        return
        
    max_size = QSize(600, 400)
    original_size = pixmap.size()
    pixmap = pixmap.scaled(max_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
    scale_factor = original_size.width() / pixmap.width() if pixmap.width() > 0 else 1.0
    
    drawing_area = DrawingArea(pixmap)
    drawing_area.scale_factor = scale_factor
    drawing_area.original_size = original_size
    layout.addWidget(drawing_area)
    
    card_option_layout = QHBoxLayout()
    card_option_layout.addWidget(QLabel("Opções de Card:"))
    card_option_group = QButtonGroup()
    single_card_radio = QRadioButton("1 Card para todos retângulos")
    single_card_radio.setChecked(True)
    multi_card_radio = QRadioButton("1 Card por retângulo")
    card_option_group.addButton(single_card_radio)
    card_option_group.addButton(multi_card_radio)
    card_option_layout.addWidget(single_card_radio)
    card_option_layout.addWidget(multi_card_radio)
    layout.addLayout(card_option_layout)
    
    text_position_layout = QHBoxLayout()
    text_position_layout.addWidget(QLabel("Posição dos Textos:"))
    text_position_combo = QComboBox()
    text_position_combo.addItems(["Em cima", "Embaixo", "À esquerda", "À direita"])
    text_position_combo.currentTextChanged.connect(lambda text: set_text_position(drawing_area, text))
    text_position_layout.addWidget(text_position_combo)
    layout.addLayout(text_position_layout)
    
    button_layout = QHBoxLayout()
    rectangle_button = QPushButton("🟨 Retângulo")
    rectangle_button.setCheckable(True)
    rectangle_button.clicked.connect(lambda checked: set_rectangle_mode(drawing_area, checked))
    button_layout.addWidget(rectangle_button)
    
    save_button = QPushButton("💾 Salvar")
    save_button.clicked.connect(lambda: save_image(
        drawing_area.edited_pixmap, 
        full_path, 
        img_field, 
        img_path, 
        self, 
        dialog, 
        drawing_area,
        "single" if single_card_radio.isChecked() else "multiple"
    ))
    button_layout.addWidget(save_button)
    layout.addLayout(button_layout)
    dialog.setLayout(layout)
    dialog.exec()

def set_rectangle_mode(drawing_area, checked):
    drawing_area.rectangle_mode = checked

def set_text_position(drawing_area, text):
    position_map = {"Em cima": "top", "Embaixo": "bottom", "À esquerda": "left", "À direita": "right"}
    drawing_area.text_position = position_map.get(text, "top")

def save_image(pixmap, full_path, img_field, img_path, editor, dialog, drawing_area, card_option="single"):
    media_dir = os.path.dirname(full_path)
    img_filename = os.path.basename(img_path)
    
    if not img_filename.lower().endswith('.png'):
        img_filename = os.path.splitext(img_filename)[0] + '.png'
        full_path = os.path.join(media_dir, img_filename)
        
    if not pixmap.save(full_path, "PNG"):
        showInfo(f"Erro ao salvar a imagem: {full_path}")
        return
        
    collection = editor.note.col
    collection.media.add_file(full_path)
    
    try:
        html_contents = generate_html(
            img_filename, 
            pixmap, 
            drawing_area.rectangles, 
            media_dir, 
            drawing_area.scale_factor, 
            drawing_area.timestamp, 
            card_option, 
            drawing_area.texts,
            drawing_area.text_position
        )
    except FileNotFoundError as e:
        showInfo(str(e))
        return
        
    if card_option == "single":
        editor.note[img_field] = html_contents[0]
        if editor.note.id != 0:
            editor.note.flush()
        editor.loadNoteKeepingFocus()
    else:
        if not drawing_area.rectangles:
            showInfo("Nenhum retângulo desenhado para criar cards!")
            return
            
        editor.note[img_field] = html_contents[0]
        if editor.note.id != 0:
            editor.note.flush()
        editor.loadNoteKeepingFocus()
        
        if len(html_contents) > 1:
            model = editor.note.model()
            deck_id = editor.note.cards()[0].did if editor.note.cards() else editor.mw.col.decks.selected()
            for i in range(1, len(html_contents)):
                new_note = editor.mw.col.new_note(model)
                for field_name in editor.note.keys():
                    if field_name == img_field:
                        new_note[field_name] = html_contents[i]
                    else:
                        new_note[field_name] = editor.note[field_name]
                editor.mw.col.add_note(new_note, deck_id)
            showInfo(f"Criados {len(html_contents)} cards com retângulos!")
    dialog.close()

def setup_image_button(buttons, editor):
    image_button = editor.addButton(
        icon=None,
        cmd="show-image",
        func=lambda self=editor: show_image_dialog(self),
        tip="Mostra a imagem do campo com imagem",
        label="🖼️"
    )
    buttons.append(image_button)
    return buttons

def add_widgets_button(card):
    mw.reviewer.web.eval("""
        console.log('Binding buttons and drag-and-drop for review');
        var bindButtons = function(attempt) {
            try {
                var container = document.querySelector('.anki-container');
                var multiContainers = document.querySelectorAll('.anki-multiple-card');
                
                function initDragAndDrop(container, isMulti, index) {
                    var texts = container.querySelectorAll('.anki-text');
                    var rects = container.querySelectorAll(isMulti ? '.anki-rect-multi' : '.anki-rect');
                    var textContainer = container.querySelector('.anki-text-container');
                    var imageContainer = container.querySelector('.anki-image-container') || 
                                        container.querySelector('div[style*="position:relative"]');
                    
                    texts.forEach(function(text) {
                        text.draggable = true;
                        text.addEventListener('dragstart', function(e) {
                            e.stopPropagation();
                            e.dataTransfer.setData('text/plain', text.id);
                            text.classList.add('dragging');
                            console.log('Dragging text: ' + text.id);
                        });
                        text.addEventListener('dragend', function() {
                            text.classList.remove('dragging');
                        });
                    });
                    
                    rects.forEach(function(rect) {
                        rect.draggable = false;
                        rect.addEventListener('dragstart', function(e) {
                            e.preventDefault();
                            e.stopPropagation();
                            console.log('Drag attempt on rect ' + rect.id + ' blocked');
                        });
                        rect.addEventListener('dragover', function(e) {
                            e.preventDefault();
                            if (!container.querySelector('.anki-text[data-rect-id="' + rect.id + '"]')) {
                                rect.classList.add('drop-target');
                            }
                        });
                        rect.addEventListener('dragleave', function() {
                            rect.classList.remove('drop-target');
                        });
                        rect.addEventListener('drop', function(e) {
                            e.preventDefault();
                            e.stopPropagation();
                            rect.classList.remove('drop-target');
                            if (container.querySelector('.anki-text[data-rect-id="' + rect.id + '"]')) {
                                console.log('Drop ignored: rect ' + rect.id + ' already has a text');
                                return;
                            }
                            var textId = e.dataTransfer.getData('text');
                            var textElement = document.getElementById(textId);
                            if (textElement) {
                                var correctText = rect.getAttribute('data-correct-text');
                                console.log('Comparing text: "' + textElement.textContent + '" with correct: "' + correctText + '"');
                                if (textElement.textContent.trim() === correctText.trim()) {
                                    textElement.classList.remove('incorrect');
                                    textElement.classList.add('correct');
                                    console.log('Correct drop: ' + textElement.textContent + ' on rect ' + rect.id);
                                } else {
                                    textElement.classList.remove('correct');
                                    textElement.classList.add('incorrect');
                                    console.log('Incorrect drop: ' + textElement.textContent + ' on rect ' + rect.id);
                                }
                                container.appendChild(textElement);
                                textElement.classList.remove('free');
                                textElement.style.position = 'absolute';
                                var rectBounds = rect.getBoundingClientRect();
                                var containerBounds = container.getBoundingClientRect();
                                var left = rectBounds.left - containerBounds.left + (rectBounds.width / 2);
                                var top = rectBounds.top - containerBounds.top + (rectBounds.height / 2);
                                textElement.style.left = left + 'px';
                                textElement.style.top = top + 'px';
                                textElement.style.transform = 'translate(-50%, -50%)';
                                textElement.setAttribute('data-rect-id', rect.id);
                            }
                        });
                    });
                    
                    if (textContainer) {
                        textContainer.addEventListener('dragover', function(e) {
                            e.preventDefault();
                            textContainer.classList.add('drop-target');
                        });
                        textContainer.addEventListener('dragleave', function() {
                            textContainer.classList.remove('drop-target');
                        });
                        textContainer.addEventListener('drop', function(e) {
                            e.preventDefault();
                            e.stopPropagation();
                            textContainer.classList.remove('drop-target');
                            var textId = e.dataTransfer.getData('text');
                            var textElement = document.getElementById(textId);
                            if (textElement) {
                                textElement.classList.remove('correct', 'incorrect', 'free');
                                textElement.style.removeProperty('position');
                                textElement.style.removeProperty('left');
                                textElement.style.removeProperty('top');
                                textElement.style.removeProperty('transform');
                                textElement.removeAttribute('data-rect-id');
                                textContainer.appendChild(textElement);
                                console.log('Text returned to container: ' + textElement.textContent);
                            }
                        });
                    }
                    
                    container.addEventListener('dragover', function(e) {
                        e.preventDefault();
                        container.classList.add('drop-target');
                    });
                    container.addEventListener('dragleave', function() {
                        container.classList.remove('drop-target');
                    });
                    container.addEventListener('drop', function(e) {
                        e.preventDefault();
                        e.stopPropagation();
                        container.classList.remove('drop-target');
                        var dropTarget = e.target;
                        if (dropTarget.closest('.anki-rect') || dropTarget.closest('.anki-rect-multi') || 
                            dropTarget.closest('.anki-text-container')) {
                            return;
                        }
                        var textId = e.dataTransfer.getData('text');
                        var textElement = document.getElementById(textId);
                        if (textElement) {
                            var rect = container.getBoundingClientRect();
                            var x = e.clientX - rect.left;
                            var y = e.clientY - rect.top;
                            textElement.classList.remove('correct', 'incorrect');
                            textElement.classList.add('free');
                            textElement.style.position = 'absolute';
                            textElement.style.left = x + 'px';
                            textElement.style.top = y + 'px';
                            textElement.style.transform = 'none';
                            textElement.removeAttribute('data-rect-id');
                            container.appendChild(textElement);
                            console.log('Text dropped freely at (' + x + ', ' + y + '): ' + textElement.textContent);
                        }
                    });
                }
                
                if (container) {
                    var showBtn = container.querySelector('[id^="showButton_"]');
                    var hideBtn = container.querySelector('[id^="hideButton_"]');
                    if (showBtn) {
                        showBtn.onclick = function() {
                            document.querySelectorAll('.anki-rect').forEach(function(rect) {
                                rect.style.display = 'block';
                                rect.style.removeProperty('display');
                                console.log('Show button reset display for rect ' + rect.id);
                            });
                            console.log('Show button clicked');
                        };
                    }
                    if (hideBtn) {
                        hideBtn.onclick = function() {
                            document.querySelectorAll('.anki-rect').forEach(function(rect) {
                                rect.style.display = 'none';
                                console.log('Hide button set none for rect ' + rect.id);
                            });
                            console.log('Hide button clicked');
                        };
                    }
                    initDragAndDrop(container, false);
                }
                
                multiContainers.forEach(function(multiContainer, index) {
                    var showBtn = multiContainer.querySelector('[id^="showBtn' + index + '_"]');
                    var hideBtn = multiContainer.querySelector('[id^="hideBtn' + index + '_"]');
                    if (showBtn) {
                        showBtn.onclick = function() {
                            var rect = multiContainer.querySelector('#rect' + index);
                            if (rect) {
                                rect.style.display = 'block';
                                rect.style.removeProperty('display');
                                console.log('Show button ' + index + ' reset display for rect' + index);
                            }
                            console.log('Show button ' + index + ' clicked');
                        };
                    }
                    if (hideBtn) {
                        hideBtn.onclick = function() {
                            var rect = multiContainer.querySelector('#rect' + index);
                            if (rect) {
                                rect.style.display = 'none';
                                console.log('Hide button ' + index + ' set none for rect' + index);
                            }
                            console.log('Hide button ' + index + ' clicked');
                        };
                    }
                    initDragAndDrop(multiContainer, true, index);
                });
                
                console.log('Button binding and drag-and-drop complete, attempt: ' + attempt);
            } catch (e) {
                console.log('Button binding error, attempt: ' + attempt + ', error: ' + e.message);
                if (attempt < 3) {
                    setTimeout(function() { bindButtons(attempt + 1); }, 1000);
                }
            }
        };
        setTimeout(function() { bindButtons(1); }, 2000);
    """)

gui_hooks.editor_did_init_buttons.append(setup_image_button)
gui_hooks.reviewer_did_show_question.append(add_widgets_button)