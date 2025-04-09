from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash
from PIL import Image, ImageDraw, ImageFont, ImageOps
from arabic_reshaper import reshape
from bidi.algorithm import get_display
import os
import sys
import textwrap
import uuid

# إضافة مسار المكتبات المحلية
sys.path.append(os.path.join(os.path.dirname(__file__), 'lib'))

# استيراد مكتبة التشكيل المحلية
try:
    from shakkala import Shakkala
    sh = Shakkala()
except ImportError as e:
    print(f"تحذير: لم يتم تحميل مكتبة التشكيل - {str(e)}")
    sh = None

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

# إعدادات المسارات
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, 'static')
GENERATED_DIR = os.path.join(STATIC_DIR, 'generated')
os.makedirs(GENERATED_DIR, exist_ok=True)

# إعدادات الخطوط
FONT_PATHS = {
    'Amiri': {
        'regular': os.path.join(STATIC_DIR, 'fonts/Amiri-Regular.ttf'),
        'bold': os.path.join(STATIC_DIR, 'fonts/Amiri-Bold.ttf')
    },
    'Aref Ruqaa': {
        'regular': os.path.join(STATIC_DIR, 'fonts/ArefRuqaa-Regular.ttf'),
        'bold': os.path.join(STATIC_DIR, 'fonts/ArefRuqaa-Bold.ttf')
    }
}

# إعدادات التصميم
DESIGNS = {
    'normal': {
        'size': (1200, 1800),
        'title_font': ('Aref Ruqaa', 'bold'),
        'text_font': ('Amiri', 'regular'),
        'bg_color': '#FFFFFF',
        'title_color': '#2c3e50',
        'text_color': '#34495e'
    },
    'luxury': {
        'size': (1500, 2200),
        'title_font': ('Aref Ruqaa', 'bold'),
        'text_font': ('Amiri', 'bold'),
        'bg_color': '#f8f1e5',
        'title_color': '#8b4513',
        'text_color': '#5d4037',
        'border_color': '#d4af37'
    }
}

def load_font(font_name, style='regular'):
    """تحميل الخط مع التعامل مع الأخطاء"""
    try:
        font_path = FONT_PATHS.get(font_name, {}).get(style)
        if font_path and os.path.exists(font_path):
            return ImageFont.truetype(font_path, size=60 if 'title' in style else 40)
    except Exception as e:
        print(f"خطأ في تحميل الخط: {str(e)}")
    
    # العودة للخط الافتراضي إذا فشل التحميل
    return ImageFont.load_default()

def apply_tashkeel(text):
    """تطبيق التشكيل باستخدام المكتبة المحلية"""
    if not sh or not text:
        return text
    
    try:
        # معالجة النص مع المكتبة المحلية
        input_text = text[:512]  # بعض المكتبات لها حد أقصى لطول النص
        result = sh.shakkala(input_text)
        return result['text'] if result else text
    except Exception as e:
        print(f"خطأ في التشكيل: {str(e)}")
        return text

def process_arabic(text, do_tashkeel=False):
    """معالجة النص العربي مع التشكيل"""
    if not text:
        return ""
    
    # تطبيق التشكيل إذا كان مطلوباً والمكتبة متوفرة
    if do_tashkeel:
        text = apply_tashkeel(text)
    
    # إعادة تشكيل الحروف العربية
    reshaped = reshape(text)
    
    # ضبط اتجاه النص
    return get_display(reshaped)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/create', methods=['GET', 'POST'])
def create():
    if request.method == 'POST':
        poem_data = {
            'title': request.form.get('title', '').strip(),
            'poet': request.form.get('poet', '').strip(),
            'poem': request.form.get('poem', '').strip(),
            'design': request.form.get('design', 'normal'),
            'poem_type': request.form.get('poem_type', 'ghazal'),
            'tashkeel': request.form.get('tashkeel') == 'on'
        }
        
        if not poem_data['title'] or not poem_data['poem']:
            flash('الرجاء إدخال عنوان القصيدة ونصها', 'error')
            return redirect(url_for('create'))
        
        img_path = generate_poem_image(poem_data)
        if img_path:
            return render_template('result.html',
                               title=poem_data['title'],
                               poet=poem_data['poet'],
                               img_path=img_path)
        else:
            flash('حدث خطأ في إنشاء التصميم', 'error')
            return redirect(url_for('create'))
    
    return render_template('create.html', designs=DESIGNS.keys())

def generate_poem_image(data):
    """إنشاء صورة القصيدة"""
    try:
        config = DESIGNS[data['design']]
        img = Image.new('RGB', config['size'], color=config['bg_color'])
        draw = ImageDraw.Draw(img)
        
        # تحميل الخطوط
        title_font = load_font(*config['title_font'])
        text_font = load_font(*config['text_font'])
        
        # معالجة النصوص
        title = process_arabic(data['title'], data['tashkeel'])
        poet = process_arabic(f"لـ {data['poet']}", data['tashkeel']) if data['poet'] else ""
        poem = process_arabic(data['poem'], data['tashkeel'])
        
        # وضع العنوان
        draw.text((img.width//2, 150), title, font=title_font,
                 fill=config['title_color'], anchor='ma')
        
        # وضع اسم الشاعر
        if poet:
            draw.text((img.width//2, 250), poet, font=text_font,
                     fill=config['text_color'], anchor='ma')
        
        # وضع نص القصيدة
        y_position = 350
        for line in textwrap.wrap(poem, width=30):
            draw.text((img.width//2, y_position), line, font=text_font,
                     fill=config['text_color'], anchor='ma')
            y_position += 60
        
        # إضافة الزخارف حسب نوع القصيدة
        add_decoration(draw, data['poem_type'], img.width, img.height)
        
        # حفظ الصورة
        img_name = f"poem_{uuid.uuid4().hex}.jpg"
        img_path = os.path.join(GENERATED_DIR, img_name)
        img.save(img_path, quality=95, optimize=True)
        
        return f"generated/{img_name}"
    
    except Exception as e:
        print(f"خطأ في إنشاء الصورة: {str(e)}")
        return None

def add_decoration(draw, poem_type, width, height):
    """إضافة زخارف حسب نوع القصيدة"""
    decorations = {
        'ghazal': {'symbol': '♥', 'color': 'red', 'position': (width-100, 100)},
        'rithaa': {'symbol': '☽', 'color': 'gray', 'position': (100, 100)},
        'zuhd': {'symbol': '☾', 'color': 'blue', 'position': (width-100, height-100)},
        'fakhr': {'symbol': '⚔', 'color': 'gold', 'position': (100, height-100)}
    }
    
    decor = decorations.get(poem_type)
    if decor:
        draw.text(decor['position'], decor['symbol'], 
                 fill=decor['color'], font=ImageFont.load_default())

@app.route('/download/<filename>')
def download(filename):
    try:
        return send_from_directory(GENERATED_DIR, filename, as_attachment=True)
    except FileNotFoundError:
        flash('الملف المطلوب غير موجود', 'error')
        return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)