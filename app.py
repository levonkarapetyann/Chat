import os
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit, join_room

app = Flask(__name__)
app.config['SECRET_KEY'] = 'super-secret-key-change-it'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
socketio = SocketIO(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    password = db.Column(db.String(100), nullable=False)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())


@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('chat'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip().lower()
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        password = request.form.get('password')

        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'danger')
            return redirect(url_for('register'))

        new_user = User(username=username, first_name=first_name, last_name=last_name, password=password)
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
        
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip().lower()
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()
        if user and user.password == password:
            session['user_id'] = user.id
            return redirect(url_for('chat'))
            
        flash('Invalid username or password', 'danger')
        return redirect(url_for('login'))
        
    return render_template('login.html')

@app.route('/chat')
def chat():
    current_user_id = session.get('user_id')
    if not current_user_id:
        return redirect(url_for('login'))

    current_user = User.query.get(current_user_id)
    if not current_user:
        return redirect(url_for('login'))
    
    sent_messages = db.session.query(Message.recipient_id).filter(Message.sender_id == current_user_id)
    rcvd_messages = db.session.query(Message.sender_id).filter(Message.recipient_id == current_user_id)
    chat_partner_ids = sent_messages.union(rcvd_messages).all()
    
    chat_partner_ids = [pid[0] for pid in chat_partner_ids]
    existing_chats = User.query.filter(User.id.in_(chat_partner_ids)).all() if chat_partner_ids else []

    return render_template('chat.html', current_user=current_user, existing_chats=existing_chats)

@app.route('/search_user', methods=['GET'])
def search_user():
    current_user_id = session.get('user_id')
    if not current_user_id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    username = request.args.get('username', '').strip().lower()
    if not username:
        return jsonify({'success': False, 'message': 'Username is empty'})
    
    me = User.query.get(current_user_id)
    if me and username == me.username.lower():
        return jsonify({'success': False, 'message': "You can't chat with yourself"})
        
    user = User.query.filter_by(username=username).first()
    if user:
        return jsonify({
            'success': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name
            }
        })
    return jsonify({'success': False, 'message': 'User not found'})

@app.route('/get_messages/<int:partner_id>')
def get_messages(partner_id):
    current_user_id = session.get('user_id')
    if not current_user_id:
        return jsonify([])

    messages = Message.query.filter(
        ((Message.sender_id == current_user_id) & (Message.recipient_id == partner_id)) |
        ((Message.sender_id == partner_id) & (Message.recipient_id == current_user_id))
    ).order_by(Message.timestamp.asc()).all()

    return jsonify([{\
        'sender_id': msg.sender_id,\
        'recipient_id': msg.recipient_id,\
        'text': msg.text,\
        'timestamp': msg.timestamp.strftime('%H:%M')\
    } for msg in messages])

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@socketio.on('join')
def on_join(data):
    user_id = session.get('user_id')
    partner_id = data['partner_id']
    room = f"room_{min(user_id, partner_id)}_{max(user_id, partner_id)}"
    join_room(room)

@socketio.on('send_message')
def handle_send_message(data):
    sender_id = session.get('user_id')
    recipient_id = int(data['recipient_id'])
    text = data['text'].strip()

    if text:
        msg = Message(sender_id=sender_id, recipient_id=recipient_id, text=text)
        db.session.add(msg)
        db.session.commit()

        room = f"room_{min(sender_id, recipient_id)}_{max(sender_id, recipient_id)}"
        emit('new_message', {
            'sender_id': sender_id,
            'text': text
        }, room=room)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    socketio.run(app, debug=True, port=5000)
