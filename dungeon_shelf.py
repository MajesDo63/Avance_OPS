from flask import Flask, render_template_string, request, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash
import boto3

# Flask Application Configuration
env_app = Flask(__name__)
env_app.secret_key = 'Nicooa6652'

# DynamoDB Configuration
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
users_table = dynamodb.Table('users')
comics_table = dynamodb.Table('comics')

# CSS Styles
style = """
<style>
    body {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        background-color: #f0f2f5;
        padding: 20px;
        color: #333;
    }
    h1, h2 {
        color: #2c3e50;
        text-align: center;
    }
    .form-container {
        max-width: 400px;
        margin: 50px auto;
        background: white;
        padding: 20px;
        border-radius: 8px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    .form-container input, .form-container button {
        width: 100%;
        padding: 10px;
        margin: 8px 0;
        border-radius: 6px;
        border: 1px solid #ccc;
    }
    .form-container button {
        background-color: #3498db;
        color: white;
        border: none;
        cursor: pointer;
    }
    .catalogo {
        display: flex;
        gap: 20px;
        flex-wrap: wrap;
        justify-content: center;
        margin-top: 30px;
    }
    .card {
        background: white;
        padding: 15px;
        border-radius: 12px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        text-align: center;
        width: 200px;
    }
    .card button {
        margin-top: 10px;
        padding: 8px;
        border: none;
        border-radius: 6px;
        background: #27ae60;
        color: white;
        cursor: pointer;
        width: 100%;
    }
    .carrito {
        max-width: 600px;
        margin: 30px auto;
        background: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    table { width: 100%; border-collapse: collapse; }
    th, td { padding: 10px; border: 1px solid #ddd; }
    th { background: #3498db; color: white; }
</style>
"""

# HTML Templates in-code
register_html = style + """
<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"><title>Registro</title></head>
<body>
  <div class="form-container">
    <h2>Crear Cuenta</h2>
    <form method="post" action="/register">
      <input name="username" type="text" placeholder="Usuario" required>
      <input name="password" type="password" placeholder="Contraseña" required>
      <button type="submit">Registrarse</button>
    </form>
    <p>¿Ya tienes cuenta? <a href="/login">Iniciar sesión</a></p>
  </div>
</body>
</html>
"""

login_html = style + """
<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"><title>Iniciar Sesión</title></head>
<body>
  <div class="form-container">
    <h2>Iniciar Sesión</h2>
    <form method="post" action="/login">
      <input name="username" type="text" placeholder="Usuario" required>
      <input name="password" type="password" placeholder="Contraseña" required>
      <button type="submit">Entrar</button>
    </form>
    <p>¿No tienes cuenta? <a href="/register">Regístrate</a></p>
  </div>
</body>
</html>
"""

main_page_html = style + """
<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"><title>DungeonShelf</title></head>
<body>
  <h1>Bienvenido, {{ username }}</h1>
  <form action="/logout" method="get"><button>Cerrar sesión</button></form>
  <h2>Catálogo</h2>
  <div class="catalogo">
    {% for comic in comics %}
    <div class="card">
      <h3>{{ comic['issue_name'] }}</h3>
      <p>Precio: ${{ comic['price'] }}</p>
      <form method="post" action="/agregar_carrito">
        <input type="hidden" name="issue_name" value="{{ comic['issue_name'] }}">
        <input type="hidden" name="price" value="{{ comic['price'] }}">
        <button type="submit">Añadir al carrito</button>
      </form>
    </div>
    {% endfor %}
  </div>
  <h2>Carrito</h2>
  <div class="carrito">
    <table>
      <tr><th>Cómic</th><th>Precio</th><th>Cantidad</th></tr>
      {% for item in carrito %}
      <tr>
        <td>{{ item['issue_name'] }}</td>
        <td>${{ item['price'] }}</td>
        <td>{{ item['quantity'] }}</td>
      </tr>
      {% endfor %}
    </table>
    <p><strong>Total:</strong> ${{ total }}</p>
  </div>
</body>
</html>
"""

# Rutas
@env_app.route('/', methods=['GET'])
def home():
    return redirect('/register')

@env_app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if not username or not password:
            return "<h3 style='color:red;'>Por favor completa todos los campos</h3><a href='/register'>Volver</a>"
        if users_table.get_item(Key={'name': username}).get('Item'):
            return "<h3 style='color:red;'>El usuario ya existe</h3><a href='/register'>Volver</a>"
        users_table.put_item(Item={'name': username, 'password': generate_password_hash(password)})
        return redirect('/login')
    return render_template_string(register_html)

@env_app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if not username or not password:
            return "<h3 style='color:red;'>Por favor completa todos los campos</h3><a href='/login'>Volver</a>"
        resp = users_table.get_item(Key={'name': username})
        user = resp.get('Item')
        if user and check_password_hash(user['password'], password):
            session['username'] = username
            session['cart'] = []
            return redirect('/index')
        return "<h3 style='color:red;'>Credenciales incorrectas</h3><a href='/login'>Volver</a>"
    return render_template_string(login_html)

@env_app.route('/index', methods=['GET'])
def index():
    if 'username' not in session:
        return redirect('/login')
    comics = comics_table.scan().get('Items', [])
    cart = session.get('cart', [])
    total = sum(item['quantity'] * float(item['price']) for item in cart)
    return render_template_string(main_page_html, username=session['username'], comics=comics, carrito=cart, total=f"{total:.2f}")

@env_app.route('/agregar_carrito', methods=['POST'])
def agregar_carrito():
    issue_name = request.form.get('issue_name')
    price = request.form.get('price')
    cart = session.get('cart', [])
    for item in cart:
        if item['issue_name'] == issue_name:
            item['quantity'] += 1
            break
    else:
        cart.append({'issue_name': issue_name, 'price': price, 'quantity': 1})
    session['cart'] = cart
    return redirect('/index')

@env_app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

if __name__ == '__main__':
    env_app.run(host='0.0.0.0', port=5000, debug=True)
