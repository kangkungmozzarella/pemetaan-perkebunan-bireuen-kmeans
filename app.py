from flask import Flask, redirect, request, render_template, url_for, session, flash, jsonify, send_file
import json
import pickle
import os
import pandas as pd
from functools import wraps
from datetime import datetime

import warnings
warnings.filterwarnings('ignore')

app = Flask(__name__,
            template_folder='templates',
            static_folder='static')
app.secret_key = "kmeans-perkebunan-bireuen-2025"

# ============================================================
# KONSTANTA
# ============================================================
KOMODITAS_LIST  = ['Karet', 'Kelapa', 'Pinang']
YEARS           = [2020, 2021, 2022, 2023, 2024]
N_CLUSTERS      = 3
CLUSTER_NAMES   = {1: 'Rendah', 2: 'Sedang', 3: 'Tinggi'}
CLUSTER_COLORS  = {1: '#4CAF50', 2: '#FF9800', 3: '#F44336'}
CLUSTERING_VARS = ['Produksi_Ton', 'Produktivitas_KgHa']

# ============================================================
# LOGIN REQUIRED DECORATOR
# ============================================================
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('Silakan login untuk mengakses halaman ini', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ============================================================
# HELPER — LOAD FILE HASIL NOTEBOOK
# ============================================================
def load_json(filename):
    """Generic loader untuk file JSON hasil notebook"""
    path = f'flask_app/static/data/{filename}'
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f'[WARNING] File tidak ditemukan: {path}')
        return None
    except Exception as e:
        print(f'[ERROR] Gagal load {path}: {e}')
        return None


def load_pickle(filename):
    """Generic loader untuk file Pickle hasil notebook"""
    path = f'flask_app/static/models/{filename}'
    try:
        with open(path, 'rb') as f:
            return pickle.load(f)
    except FileNotFoundError:
        print(f'[WARNING] File tidak ditemukan: {path}')
        return None
    except Exception as e:
        print(f'[ERROR] Gagal load {path}: {e}')
        return None


def check_data_status():
    """Cek ketersediaan semua file hasil notebook"""
    files = {
        'kmeans_summary'     : 'data/kmeans_summary.json',
        'evaluasi_clustering': 'data/evaluasi_clustering.json',
        'final_results'      : 'data/final_results.json',
        'dataset_csv'        : 'data/perkebunan_bireuen_original.csv',
        'kmeans_model'       : 'models/kmeans_results.pkl'
    }
    status = {}
    for key, path in files.items():
        status[key] = os.path.exists(f'flask_app/static/{path}')
    status['all_ready'] = all(status.values())
    return status


def get_dataset_info(final):
    """Jumlah kecamatan & record dari final_results.json"""
    info = (final or {}).get('project_info', {})
    return info.get('total_kec', 17), info.get('total_records', 255)


def get_summary_stats(summary):
    """
    Hitung statistik ringkas dari kmeans_summary.json
    untuk ditampilkan di dashboard.
    """
    if not summary:
        return None

    stats = {}
    for komoditas in KOMODITAS_LIST:
        if komoditas not in summary:
            continue
        stats[komoditas] = {}
        for tahun in YEARS:
            key = str(tahun)
            if key not in summary[komoditas]:
                continue
            d = summary[komoditas][key]
            stats[komoditas][tahun] = {
                'silhouette_score': d.get('silhouette_score', 0),
                'dbi_score'       : d.get('dbi_score', 0),
                'n_iter'          : d.get('n_iter', 0),
                'inertia'         : d.get('inertia', 0),
                'distribusi'      : d.get('distribusi', {}),
            }
    return stats

# ============================================================
# ROUTES — HOMEPAGE
# ============================================================
@app.route('/')
def homepage():
    """Homepage publik"""
    total_kecamatan, total_records = get_dataset_info(load_json('final_results.json'))
    return render_template('index.html',
        total_kecamatan = total_kecamatan,
        total_records   = total_records
    )

# ============================================================
# ROUTES — LOGIN / LOGOUT
# ============================================================
@app.route('/admin/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == 'admin' and password == 'admin123':
            session['username'] = username
            session['status']   = 'Login'
            flash(f'Selamat datang, {username}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Username atau Password salah', 'danger')
    return render_template('admin/login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('Anda telah logout', 'info')
    return redirect(url_for('homepage'))

# ============================================================
# ROUTES — DASHBOARD
# ============================================================
@app.route('/dashboard')
@login_required
def dashboard():
    """Dashboard utama — ringkasan K-Means semua komoditas"""
    summary  = load_json('kmeans_summary.json')
    evaluasi = load_json('evaluasi_clustering.json')
    final    = load_json('final_results.json')
    status   = check_data_status()
    stats    = get_summary_stats(summary)
    total_kecamatan, total_records = get_dataset_info(final)

    # Hitung statistik untuk header cards
    best_komoditas  = None
    avg_sil         = None
    avg_dbi         = None

    if evaluasi:
        df_eval = pd.DataFrame(evaluasi)
        avg_sil = round(df_eval['Silhouette Score'].mean(), 4)
        avg_dbi = round(df_eval['DBI Score'].mean(), 4)

        # Komoditas dengan rata-rata DBI terkecil (terbaik)
        dbi_per_kom = df_eval.groupby('Komoditas')['DBI Score'].mean()
        best_komoditas = dbi_per_kom.idxmin()

    return render_template('dashboard/index.html',
        summary         = summary,
        evaluasi        = evaluasi,
        final           = final,
        status          = status,
        stats           = stats,
        komoditas_list  = KOMODITAS_LIST,
        years           = YEARS,
        n_clusters      = N_CLUSTERS,
        cluster_names   = CLUSTER_NAMES,
        cluster_colors  = CLUSTER_COLORS,
        clustering_vars = CLUSTERING_VARS,
        best_komoditas  = best_komoditas,
        avg_sil         = avg_sil,
        avg_dbi         = avg_dbi,
        total_komoditas = len(KOMODITAS_LIST),
        total_kecamatan = total_kecamatan,
        total_records   = total_records
    )

# ============================================================
# ROUTES — DATASET
# ============================================================
@app.route('/dataset')
@login_required
def dataset():
    """Halaman dataset perkebunan"""
    try:
        df       = pd.read_csv('flask_app/static/data/perkebunan_bireuen_original.csv')
        datasets = df.to_dict(orient='records')
    except Exception:
        datasets = []

    return render_template('dataset/index.html', datasets=datasets)


@app.route('/dataset/download')
@login_required
def dataset_download():
    """Download dataset bersih hasil notebook"""
    return send_file('flask_app/static/data/perkebunan_bireuen_original.csv',
                     as_attachment=True,
                     download_name='perkebunan_bireuen.csv')

# ============================================================
# ROUTES — HASIL ANALISIS
# ============================================================
@app.route('/hasil-analisis')
@login_required
def hasil_analisis():
    """Halaman hasil analisis K-Means lengkap"""
    summary  = load_json('kmeans_summary.json')
    evaluasi = load_json('evaluasi_clustering.json')
    final    = load_json('final_results.json')
    status   = check_data_status()
    total_kecamatan, total_records = get_dataset_info(final)

    # Hitung yearly stats untuk tabel evaluasi
    yearly_stats = []
    if evaluasi:
        for row in evaluasi:
            yearly_stats.append({
                'komoditas'        : row['Komoditas'],
                'year'             : row['Tahun'],
                'silhouette_score' : row['Silhouette Score'],
                'dbi_score'        : row['DBI Score'],
                'n_iter'           : row['Iterasi'],
                'inertia'          : row['Inertia'],
                'cluster_rendah'   : row['Cluster Rendah'],
                'cluster_sedang'   : row['Cluster Sedang'],
                'cluster_tinggi'   : row['Cluster Tinggi'],
            })

    return render_template('hasil-analisis/index.html',
        summary         = summary,
        evaluasi        = evaluasi,
        final           = final,
        status          = status,
        yearly_stats    = yearly_stats,
        komoditas_list  = KOMODITAS_LIST,
        years           = YEARS,
        n_clusters      = N_CLUSTERS,
        cluster_names   = CLUSTER_NAMES,
        cluster_colors  = CLUSTER_COLORS,
        clustering_vars = CLUSTERING_VARS,
        total_kecamatan = total_kecamatan,
        total_records   = total_records
    )

# ============================================================
# ROUTES — TENTANG
# ============================================================
@app.route('/tentang')
def tentang():
    """Halaman tentang penelitian + ringkasan komoditas tahun terakhir"""
    final = load_json('final_results.json')
    total_kecamatan, total_records = get_dataset_info(final)

    ringkasan = {}
    tahun_akhir = max(YEARS)
    try:
        df = pd.read_csv('flask_app/static/data/perkebunan_bireuen_original.csv')
        df = df[df['Tahun'] == tahun_akhir]
        for komoditas, d in df.groupby('Komoditas'):
            top = d.loc[d['Produksi_Ton'].idxmax()]
            ringkasan[komoditas] = {
                'total_produksi'    : d['Produksi_Ton'].sum(),
                'rata_produktivitas': d['Produktivitas_KgHa'].mean(),
                'kec_tertinggi'     : top['Kecamatan'],
                'produksi_tertinggi': top['Produksi_Ton'],
            }
    except Exception:
        pass

    return render_template('tentang/index.html',
        ringkasan       = ringkasan,
        tahun_akhir     = tahun_akhir,
        total_kecamatan = total_kecamatan,
        total_records   = total_records,
        clustering_vars = CLUSTERING_VARS,
        n_clusters      = N_CLUSTERS
    )

# ============================================================
# API — SUMMARY (semua komoditas semua tahun)
# ============================================================
@app.route('/api/summary')
def api_summary():
    """Return kmeans_summary.json"""
    summary = load_json('kmeans_summary.json')
    if summary is None:
        return jsonify({'error': 'File belum tersedia. Jalankan notebook terlebih dahulu.'}), 503
    return jsonify(summary)


# ============================================================
# API — CLUSTERING PER KOMODITAS PER TAHUN
# ============================================================
@app.route('/api/clustering/<komoditas>/<int:tahun>')
def api_clustering(komoditas, tahun):
    """
    Return data clustering untuk komoditas dan tahun tertentu.
    Contoh: /api/clustering/Karet/2024
    """
    if komoditas not in KOMODITAS_LIST:
        return jsonify({'error': f'Komoditas tidak valid: {komoditas}'}), 400
    if tahun not in YEARS:
        return jsonify({'error': f'Tahun tidak valid: {tahun}'}), 400

    summary = load_json('kmeans_summary.json')
    if summary is None:
        return jsonify({'error': 'File belum tersedia'}), 503

    data = summary.get(komoditas, {}).get(str(tahun))
    if data is None:
        return jsonify({'error': f'Data {komoditas} {tahun} tidak ditemukan'}), 404

    return jsonify(data)


# ============================================================
# API — EVALUASI
# ============================================================
@app.route('/api/evaluasi')
def api_evaluasi():
    """Return evaluasi_clustering.json"""
    evaluasi = load_json('evaluasi_clustering.json')
    if evaluasi is None:
        return jsonify({'error': 'File belum tersedia'}), 503
    return jsonify(evaluasi)


# ============================================================
# API — STATUS FILE
# ============================================================
@app.route('/api/status')
def api_status():
    """Cek status ketersediaan file hasil notebook"""
    return jsonify(check_data_status())


# ============================================================
# API — PETA (URL gambar peta per komoditas per tahun)
# ============================================================
@app.route('/api/peta/<komoditas>/<int:tahun>')
def api_peta(komoditas, tahun):
    if komoditas not in KOMODITAS_LIST:
        return jsonify({'error': 'Komoditas tidak valid'}), 400

    filename  = f'peta_{komoditas.lower()}_{tahun}.png'
    full_path = os.path.join('static', 'images', 'maps', filename)
    available = os.path.exists(full_path)

    return jsonify({
        'komoditas' : komoditas,
        'tahun'     : tahun,
        'filename'  : filename,
        'url'       : f'/static/images/maps/{filename}' if available else None,
        'available' : available,
    })

# ============================================================
# USER MANAGEMENT
# ============================================================
USERS = {
    'admin': {
        'id'       : 1,
        'nama_user': 'Administrator',
        'username' : 'admin',
        'password' : 'admin123'
    }
}

@app.route('/users')
@login_required
def users():
    return render_template('users/index.html', users=list(USERS.values()))


@app.route('/users/add', methods=['POST'])
@login_required
def users_add():
    nama_user = request.form['nama_user']
    username  = request.form['username']
    password  = request.form['password']

    if username in USERS:
        flash('Username sudah ada.', 'danger')
    else:
        new_id = max(u['id'] for u in USERS.values()) + 1
        USERS[username] = {
            'id': new_id, 'nama_user': nama_user,
            'username': username, 'password': password
        }
        flash('User berhasil ditambahkan!', 'success')
    return redirect(url_for('users'))


@app.route('/users/update', methods=['POST'])
@login_required
def users_update():
    user_id   = int(request.form['id'])
    nama_user = request.form['nama_user']
    username  = request.form['username']
    password  = request.form['password']

    old_username = next(
        (u for u, d in USERS.items() if d['id'] == user_id), None
    )

    if old_username:
        if username in USERS and username != old_username:
            flash('Username sudah ada.', 'danger')
        else:
            if username != old_username:
                del USERS[old_username]
            USERS[username] = {
                'id': user_id, 'nama_user': nama_user,
                'username': username,
                'password': password or USERS.get(
                    old_username, {}
                ).get('password', '')
            }
            if session.get('username') == old_username:
                session['username'] = username
            flash('User berhasil diupdate!', 'success')
    else:
        flash('User tidak ditemukan!', 'danger')

    return redirect(url_for('users'))


@app.route('/users/delete', methods=['POST'])
@login_required
def users_delete():
    user_id = int(request.form['id'])
    username_to_delete = next(
        (u for u, d in USERS.items() if d['id'] == user_id), None
    )

    if username_to_delete:
        if username_to_delete == session.get('username'):
            flash('Tidak dapat menghapus akun sendiri saat login.', 'danger')
        else:
            del USERS[username_to_delete]
            flash('User berhasil dihapus!', 'success')
    else:
        flash('User tidak ditemukan!', 'danger')

    return redirect(url_for('users'))

# ============================================================
# ERROR HANDLERS
# ============================================================
@app.errorhandler(404)
def not_found(error):
    return render_template('layouts/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('layouts/500.html'), 500

# ============================================================
# TEMPLATE FILTER
# ============================================================
@app.template_filter('angka')
def format_angka(value, desimal=2):
    """Format angka gaya Indonesia: 1747.5 → 1.747,50"""
    try:
        teks = f'{float(value):,.{desimal}f}'
    except (TypeError, ValueError):
        return value
    return teks.replace(',', '_').replace('.', ',').replace('_', '.')

# ============================================================
# CONTEXT PROCESSOR
# ============================================================
@app.context_processor
def inject_global_vars():
    return {
        'app_name'       : 'Pemetaan Geospasial Perkebunan Bireuen',
        'app_description': 'Sistem Pemetaan Geospasial Hasil Perkebunan di Kabupaten Bireuen menggunakan K-Means Clustering',
        'current_year'   : datetime.now().year,
        'is_logged_in'   : 'username' in session,
        'current_user'   : session.get('username', 'Guest'),
        'komoditas_list' : KOMODITAS_LIST,
        'years'          : YEARS
    }

# ============================================================
# MAIN
# ============================================================
if __name__ == '__main__':
    print('\n' + '='*55)
    print('  Pemetaan Geospasial Perkebunan — Kabupaten Bireuen')
    print('  K-Means Clustering')
    print('='*55)

    status = check_data_status()
    print('\nStatus file hasil notebook:')
    for key, ready in status.items():
        if key == 'all_ready':
            continue
        icon = '✅' if ready else '⚠️  BELUM ADA'
        print(f'  {icon}  {key}')

    if not status['all_ready']:
        print('\n⚠️  Beberapa file belum tersedia.')
        print('   Jalankan notebook kmeans.ipynb terlebih dahulu.\n')
    else:
        print('\n✅ Semua file siap. Flask siap dijalankan.\n')

    app.run(debug=True, host='0.0.0.0', port=5000)