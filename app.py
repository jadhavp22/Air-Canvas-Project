from flask import Flask, render_template, Response, request, redirect, url_for, session, jsonify
import cv2
import os
import datetime
import numpy as np

app = Flask(__name__)
app.secret_key = 'your_secret_key'

drawing_color = (255, 0, 0)  # Default color blue
brush_size = 5
canvas = None
background = None

# Dummy database
users = {
    'guest': 'guest',  # Free user
    'air': 'air'       # Premium user
}

user_roles = {
    'guest': 'free',
    'air': 'premium'
}

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username in users and users[username] == password:
            session['user'] = username
            session['role'] = user_roles.get(username, 'free')
            session['login_time'] = datetime.datetime.now().strftime('%d-%m-%Y %H:%M:%S')
            return redirect('/index')
        else:
            return render_template('login.html', error='Invalid Credentials')

    return render_template('login.html')

@app.route('/index')
def index():
    if 'user' not in session:
        return redirect('/')

    saved_path = 'static/saved'
    files = os.listdir(saved_path) if os.path.exists(saved_path) else []
    drawings = sorted(files, reverse=True)[:5]

    return render_template('index.html', drawings=drawings)

@app.route('/tutorial')
def tutorial():
    if 'user' not in session:
        return redirect('/')

    saved_path = 'static/saved'
    files = os.listdir(saved_path) if os.path.exists(saved_path) else []
    drawings = sorted(files, reverse=True)[:5]

    return render_template('tutorial.html', drawings=drawings)

@app.route('/drawing')
def drawing():
    if 'user' not in session:
        return redirect('/')

    saved_path = 'static/saved'
    files = os.listdir(saved_path) if os.path.exists(saved_path) else []
    drawings = sorted(files, reverse=True)[:5]

    return render_template('drawing.html', drawings=drawings)

@app.route('/thankyou')
def thankyou():
    if 'user' not in session:
        return redirect('/')

    saved_path = 'static/saved'
    files = os.listdir(saved_path) if os.path.exists(saved_path) else []
    drawings = sorted(files, reverse=True)[:5]

    return render_template('thankyou.html', drawings=drawings)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/upgrade', methods=['GET', 'POST'])
def upgrade():
    if 'user' in session and session.get('role') == 'free':
        session['role'] = 'premium'
        return render_template('success.html')
    return redirect('/index')

@app.route('/set_drawing_color')
def set_drawing_color():
    global drawing_color, brush_size
    color = request.args.get('color', 'blue')
    size = int(request.args.get('size', 5))

    if color.startswith('#'):
        hex_color = color.lstrip('#')
        drawing_color = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    else:
        color_dict = {
            'red': (0, 0, 255),
            'green': (0, 255, 0),
            'blue': (255, 0, 0),
            'black': (0, 0, 0),
            'white': (255, 255, 255)
        }
        drawing_color = color_dict.get(color, (255, 0, 0))

    brush_size = size
    return ('', 204)

@app.route('/clear_canvas')
def clear_canvas():
    global canvas, background
    canvas = None
    background = None
    return ('', 204)

@app.route('/upload_image', methods=['POST'])
def upload_image():
    global background

    if 'user' not in session:
        return jsonify(success=False, message="Unauthorized")

    if session.get('role') != 'premium':
        return jsonify(success=False, message="Upgrade to Premium to upload!")

    file = request.files.get('image')
    if file:
        filepath = 'static/uploads/' + file.filename
        file.save(filepath)
        background = cv2.imread(filepath)
        return jsonify(success=True, path=url_for('static', filename='uploads/' + file.filename))
    else:
        return jsonify(success=False, message="No file uploaded")

@app.route('/save_image')
def save_image():
    if 'user' not in session:
        return jsonify(success=False, message="Unauthorized")

    if session.get('role') != 'premium':
        return jsonify(success=False, message="Upgrade to Premium to Save!")

    if canvas is None:
        return jsonify(success=False, message="Nothing to Save")

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f'static/saved/drawing_{timestamp}.png'
    cv2.imwrite(filename, canvas)
    return jsonify(success=True, path=url_for('static', filename=f'saved/drawing_{timestamp}.png'))

def generate_frames():
    global canvas, background
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

    if not cap.isOpened():
        print("[ERROR] Cannot open camera")
        return

    white_canvas = 255 * np.ones((480, 640, 3), dtype=np.uint8)

    prev_point = None  # <-- Add here to track last point

    while True:
        global canvas
        if canvas is None:
            canvas = white_canvas.copy()

        success, frame = cap.read()
        if not success:
            print("[ERROR] Failed to grab frame")
            break

        frame = cv2.flip(frame, 1)

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        lower_blue = (90, 50, 50)
        upper_blue = (130, 255, 255)
        mask = cv2.inRange(hsv, lower_blue, upper_blue)

        contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        if contours and len(contours) > 0:
            max_contour = max(contours, key=cv2.contourArea)

            if cv2.contourArea(max_contour) > 1000:
                x, y, w, h = cv2.boundingRect(max_contour)
                center = (x + w // 2, y + h // 2)

                if prev_point is None:
                    prev_point = center
                else:
                    cv2.line(canvas, prev_point, center, drawing_color, brush_size)
                    prev_point = center
        else:
            prev_point = None

        if background is not None:
            bg_resized = cv2.resize(background, (canvas.shape[1], canvas.shape[0]))
            output = cv2.addWeighted(canvas, 0.7, bg_resized, 0.3, 0)
        else:
            output = canvas

        if output is None or output.size == 0:
            print("[WARNING] Empty frame detected, skipping...")
            continue

        ret, buffer = cv2.imencode('.jpg', output)
        if not ret:
            print("[WARNING] Frame encoding failed")
            continue

        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

    cap.release()

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == "__main__":
    if not os.path.exists('static/uploads'):
        os.makedirs('static/uploads')
    if not os.path.exists('static/saved'):
        os.makedirs('static/saved')
    app.run(debug=True)
