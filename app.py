from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_socketio import SocketIO, emit, join_room
import os

from models import db, User, Post, Like, Comment, Message

# --------------------------------
# APP CONFIG
# --------------------------------
app = Flask(__name__)

app.config['SECRET_KEY'] = 'dev-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'

db.init_app(app)

socketio = SocketIO(app)

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

# --------------------------------
# LOGIN LOADER
# --------------------------------
@login_manager.user_loader
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))



# --------------------------------
# CREATE DATABASE
# --------------------------------
with app.app_context():
    db.create_all()


# --------------------------------
# ROUTES
# --------------------------------
@app.route('/')
@login_required
def index():
    posts = Post.query.order_by(Post.timestamp.desc()).all()
    return render_template('index.html', posts=posts)


# -------- AUTH --------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password, request.form['password']):
            login_user(user)
            return redirect(url_for('index'))
        flash('Invalid credentials')

    return render_template('login.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        hashed = generate_password_hash(request.form['password'])
        user = User(
            username=request.form['username'],
            email=request.form['email'],
            password=hashed
        )
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('login'))

    return render_template('signup.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


# -------- PROFILE --------
@app.route('/profile/<username>')
@login_required
def profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    return render_template('profile.html', user=user)


@app.route('/edit-profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        current_user.bio = request.form['bio']

        file = request.files.get('profile_pic')
        if file and file.filename:
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            current_user.profile_pic = filename

        db.session.commit()
        return redirect(url_for('profile', username=current_user.username))

    return render_template('edit_profile.html')


# -------- POSTS --------
@app.route('/create', methods=['GET', 'POST'])
@login_required
def create_post():
    if request.method == 'POST':
        file = request.files['image']
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        post = Post(
            image=filename,
            caption=request.form['caption'],
            author=current_user
        )
        db.session.add(post)
        db.session.commit()

        return redirect(url_for('index'))

    return render_template('create_post.html')

# -------- LIKE POST --------
@app.route('/like/<int:post_id>', methods=['POST'])
@login_required
def like_post(post_id):
    post = Post.query.get_or_404(post_id)

    existing_like = Like.query.filter_by(
        user_id=current_user.id,
        post_id=post.id
    ).first()

    if existing_like:
        db.session.delete(existing_like)
    else:
        like = Like(user_id=current_user.id, post_id=post.id)
        db.session.add(like)

    db.session.commit()
    return redirect(request.referrer)


# -------- COMMENT POST --------
@app.route('/comment/<int:post_id>', methods=['POST'])
@login_required
def comment_post(post_id):
    post = Post.query.get_or_404(post_id)
    content = request.form.get('comment')

    if content:
        comment = Comment(
            content=content,
            user_id=current_user.id,
            post_id=post.id
        )
        db.session.add(comment)
        db.session.commit()

    return redirect(request.referrer)

# -------- SEARCH USERS --------
@app.route('/search')
@login_required
def search():
    query = request.args.get('q', '')

    users = []
    if query:
        users = User.query.filter(
            User.username.ilike(f"%{query}%")
        ).all()

    return render_template('search.html', users=users, query=query)

# -------- MESSAGES --------
@app.route('/messages')
@login_required
def messages():
    users = User.query.filter(User.id != current_user.id).all()
    return render_template('messages.html', users=users)


@app.route('/chat/<username>')
@login_required
def chat(username):
    user = User.query.filter_by(username=username).first_or_404()
    msgs = Message.query.filter(
        ((Message.sender == current_user) & (Message.receiver == user)) |
        ((Message.sender == user) & (Message.receiver == current_user))
    ).order_by(Message.timestamp.asc()).all()

    return render_template('chat.html', user=user, messages=msgs)


# -------- SOCKET IO --------
@socketio.on('send_message')
def handle_message(data):
    receiver = User.query.get(data['receiver_id'])

    msg = Message(
        sender=current_user,
        receiver=receiver,
        content=data['message']
    )
    db.session.add(msg)
    db.session.commit()

    emit('receive_message', {
        'message': msg.content,
        'sender': current_user.username
    }, room=str(receiver.id))


@socketio.on('join')
def on_join():
    join_room(str(current_user.id))


# --------------------------------
# RUN
# --------------------------------
if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=10000)
