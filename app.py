import os
from flask import Flask, render_template_string, request, jsonify
from datetime import datetime

app = Flask(__name__)

# Lista de registros individuales en memoria
inventario_registros = []

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Control de Producción Textil</title>
    <!-- Librerías JS: ZXing (Lectura), kjua (Generación QR) y html2canvas -->
    <script src="https://unpkg.com/@zxing/library@latest"></script>
    <script src="https://cdn.jsdelivr.net/npm/kjua@0.9.0/dist/kjua.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
    <style>
        body { font-family: system-ui, -apple-system, sans-serif; margin: 15px; background: #f3f4f6; color: #1f2937; }
        .container { max-width: 500px; margin: auto; background: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }
        h2, h3 { color: #1e3a8a; margin-top: 0; }
        .section { background: #f8fafc; border: 1px solid #e2e8f0; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
        video, img { width: 100%; border-radius: 8px; background: #000; margin-top: 10px; }
        button { width: 100%; padding: 10px 14px; background: #2563eb; color: white; border: none; border-radius: 6px; font-size: 15px; font-weight: 600; margin-top: 8px; cursor: pointer; }
        button.success { background: #16a34a; }
        button.danger { background: #dc2626; }
        button.secondary { background: #475569; }
        input[type="text"], input[type="number"], input[type="date"], select, input[type="file"] { 
            width: calc(100% - 18px); padding: 8px; margin-top: 4px; margin-bottom: 10px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 14px; 
        }
        .card { background: #eff6ff; border-left: 4px solid #2563eb; padding: 12px; margin-top: 10px; border-radius: 6px; }
        .info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 14px; margin-top: 8px; }
        .info-item { background: white; padding: 8px; border-radius: 4px; border: 1px solid #dbeafe; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { border: 1px solid #e2e8f0; padding: 8px; text-align: left; font-size: 13px; }
        th { background: #f1f5f9; }
        .tab-buttons { display: flex; gap: 8px; margin-bottom: 10px; }
        .tab-buttons button { margin-top: 0; font-size: 13px; }

        #area-impresion {
            background: #ffffff !important;
            padding: 20px !important;
            border-radius: 8px;
            text-align: center;
            margin-top: 15px;
            box-shadow: 0 0 0 1px #cbd5e1;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }

        #qrcode { margin-top: 10px; }

        @media print {
            body * { visibility: hidden; }
            #area-impresion, #area-impresion * { visibility: visible; }
            #area-impresion { position: absolute; left: 0; top: 0; width: 100%; text-align: center; }
        }
    </style>
</head>
<body>
    <div class="container">
        <h2>🏭 Control de Producción Textil</h2>

        <!-- MÓDULO 1: ESCÁNER (CÁMARA / GALERÍA) -->
        <div class="section">
            <h3>🔍 Leer Código QR / Barras</h3>
            
            <div class="tab-buttons">
                <button onclick="modoCamara()" class="secondary">📷 Usar Cámara</button>
                <button onclick="modoGaleria()" class="secondary">🖼️ De Galería</button>
            </div>

            <!-- Cámara -->
            <div id="box-camara" style="display:none;">
                <button onclick="startScanner()">Activar Cámara</button>
                <video id="video" style="display:none;"></video>
            </div>

            <!-- Galería -->
            <div id="box-galeria" style="display:none;">
                <label>Selecciona la foto guardada:</label>
                <input type="file" id="file-input" accept="image/*" onchange="escanearImagen(event)">
                <img id="img-preview" style="display:none; max-height:180px; object-fit:contain; background:#fff; padding:5px; border:1px solid #ccc; margin-top:10px;">
            </div>

            <!-- RESULTADO DE LECTURA DESGLOSADO -->
            <div id="res-box" class="card" style="display:none;">
                <h4 style="margin:0 0 8px 0; color:#1e40af;">Detalles de Lote / Producción</h4>
                
                <div class="info-grid">
                    <div class="info-item">📦 <b>Título Tex:</b> <br><span id="det-titulo">---</span></div>
                    <div class="info-item">🧵 <b>Tipo Rafia:</b> <br><span id="det-tipo-rafia">---</span></div>
                    <div class="info-item">⏱️ <b>Turno:</b> <br><span id="det-turno">---</span></div>
                    <div class="info-item">📅 <b>Fecha:</b> <br><span id="det-fecha">---</span></div>
                    <div class="info-item">⚖️ <b>Peso Etiqueta:</b> <br><span id="det-peso">---</span> kg</div>
                    <div class="info-item">🧶 <b># Conos:</b> <br><span id="det-conos">---</span></div>
                    <div class="info-item" style="grid-column: span 2;">👤 <b>Responsable:</b> <br><span id="det-responsable">---</span></div>
                </div>

                <div style="margin-top: 12px; border-top: 1px dashed #bfdbfe; padding-top: 8px;">
                    <p style="margin: 4px 0 10px 0; font-size: 15px;">
                        📊 Stock Total en Almacén: <b id="p-stock" style="color: #16a34a; font-size: 17px;">0</b> <b>kg</b>
                    </p>
                    <label>Peso a procesar (kg):</label>
                    <input type="number" id="cant-peso" step="any" placeholder="Peso en kg">
                    
                    <div style="display: flex; gap: 8px;">
                        <button onclick="registrar('entrada')" class="success">+ Entrada</button>
                        <button onclick="registrar('salida')" class="danger">- Salida</button>
                    </div>
                </div>
            </div>
        </div>

        <!-- MÓDULO 2: GENERADOR DE ETIQUETAS -->
        <div class="section">
            <h3>🏷️ Crear Etiqueta de Producción</h3>
            
            <label>Título Tex:</label>
            <select id="gen-titulo">
                <option value="55 - 2.3">55 - 2.3</option>
                <option value="63 - 2.1">63 - 2.1</option>
                <option value="65 - 2.5">65 - 2.5</option>
                <option value="66 - 2.3">66 - 2.3</option>
                <option value="70 - 2.4">70 - 2.4</option>
                <option value="75 - 3.1">75 - 3.1</option>
                <option value="83 - 3.1">83 - 3.1</option>
                <option value="85 - 2.5" selected>85 - 2.5</option>
                <option value="91 - 3.1">91 - 3.1</option>
                <option value="110 - 3.1">110 - 3.1</option>
                <option value="114 - 3.3">114 - 3.3</option>
                <option value="147 - 3.3">147 - 3.3</option>
            </select>

            <label>Tipo de Rafia:</label>
            <select id="gen-tipo-rafia">
                <option value="Urdimbre">Urdimbre</option>
                <option value="Trama">Trama</option>
            </select>

            <label>Turno:</label>
            <select id="gen-turno">
                <option value="Turno 1">Turno 1</option>
                <option value="Turno 2">Turno 2</option>
                <option value="Turno 3" selected>Turno 3</option>
            </select>

            <label>Fecha:</label>
            <input type="date" id="gen-fecha">

            <label>Peso (kg):</label>
            <input type="number" step="any" id="gen-peso" placeholder="Ej: 300">

            <label># Conos:</label>
            <input type="number" id="gen-conos" placeholder="Ej: 295" value="295">

            <label>Responsable:</label>
            <select id="gen-responsable">
                <option value="Didier Estrada">Didier Estrada</option>
                <option value="Diego Castañeda" selected>Diego Castañeda</option>
                <option value="Jonathan Ortiz">Jonathan Ortiz</option>
                <option value="Yirman Doria">Yirman Doria</option>
                <option value="Alexander Duque">Alexander Duque</option>
            </select>
            
            <button onclick="generarEtiqueta()" class="secondary">Generar Etiqueta</button>
            
            <!-- Vista previa de etiqueta QR -->
            <div id="area-impresion" style="display:none;">
                <b id="lbl-nombre" style="font-size: 20px; font-weight: bold; color:#000;">---</b>
                <div id="qrcode"></div>
            </div>
            
            <div id="acciones-etiqueta" style="display:none; gap: 8px; margin-top: 10px;">
                <button onclick="guardarComoImagen()" class="success">🖼️ Guardar Imagen</button>
                <button onclick="window.print()" class="secondary">🖨️ Imprimir</button>
            </div>
        </div>

        <!-- MÓDULO 3: TABLA DE INVENTARIO -->
        <div class="section">
            <h3>📋 Inventario Registrado (Historial)</h3>
            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Título Tex</th>
                        <th>Detalles</th>
                        <th>Tipo Mov.</th>
                        <th>Peso (kg)</th>
                    </tr>
                </thead>
                <tbody id="tabla-body"></tbody>
            </table>
        </div>
    </div>

    <script>
        const codeReader = new ZXing.BrowserMultiFormatReader();
        let datosProductoActual = {};

        document.getElementById('gen-fecha').valueAsDate = new Date();

        function limpiarTexto(texto) {
            if (!texto) return '';
            texto = texto.replace(/^\uFEFF/, '').replace(/^ï»¿/, '');
            try {
                if (/[\xC2-\xF4][\x80-\xBF]/.test(texto)) {
                    texto = decodeURIComponent(escape(texto));
                }
            } catch (e) {}
            return texto.trim();
        }

        function modoCamara() {
            document.getElementById('box-camara').style.display = 'block';
            document.getElementById('box-galeria').style.display = 'none';
        }

        function modoGaleria() {
            document.getElementById('box-camara').style.display = 'none';
            document.getElementById('box-galeria').style.display = 'block';
            if (document.getElementById('video')) {
                codeReader.reset();
                document.getElementById('video').style.display = 'none';
            }
        }

        async function startScanner() {
            const videoElem = document.getElementById('video');
            videoElem.style.display = 'block';
            try {
                const devices = await codeReader.listVideoInputDevices();
                const selectedDeviceId = devices.length > 1 ? devices[1].deviceId : devices[0].deviceId;

                codeReader.decodeFromVideoDevice(selectedDeviceId, 'video', (result) => {
                    if (result) {
                        procesarCodigoCodificado(limpiarTexto(result.text));
                        videoElem.style.display = 'none';
                        codeReader.reset();
                    }
                });
            } catch (err) {
                alert("Error al abrir cámara: " + err);
            }
        }

        async function escanearImagen(e) {
            const file = e.target.files[0];
            if (!file) return;

            const imgElem = document.getElementById('img-preview');
            imgElem.src = URL.createObjectURL(file);
            imgElem.style.display = 'block';

            imgElem.onload = async () => {
                try {
                    const result = await codeReader.decodeFromImageElement(imgElem);
                    if (result) {
                        procesarCodigoCodificado(limpiarTexto(result.text));
                    }
                } catch (err) {
                    alert("No se pudo detectar el código QR en la foto.");
                }
            };
        }

        function procesarCodigoCodificado(textoCodigo) {
            let partes = textoCodigo.split('|');

            if (partes.length >= 7) {
                datosProductoActual = {
                    titulo: limpiarTexto(partes[0]),
                    tipo_rafia: limpiarTexto(partes[1]),
                    turno: limpiarTexto(partes[2]),
                    fecha: limpiarTexto(partes[3]),
                    peso: limpiarTexto(partes[4]),
                    conos: limpiarTexto(partes[5]),
                    responsable: limpiarTexto(partes[6])
                };
            } else if (partes.length === 6) {
                datosProductoActual = {
                    titulo: limpiarTexto(partes[0]),
                    tipo_rafia: "N/A",
                    turno: limpiarTexto(partes[1]),
                    fecha: limpiarTexto(partes[2]),
                    peso: limpiarTexto(partes[3]),
                    conos: limpiarTexto(partes[4]),
                    responsable: limpiarTexto(partes[5])
                };
            } else {
                datosProductoActual = {
                    titulo: limpiarTexto(textoCodigo),
                    tipo_rafia: "N/A",
                    turno: "N/A",
                    fecha: "N/A",
                    peso: "0",
                    conos: "N/A",
                    responsable: "N/A"
                };
            }

            document.getElementById('det-titulo').innerText = datosProductoActual.titulo;
            document.getElementById('det-tipo-rafia').innerText = datosProductoActual.tipo_rafia;
            document.getElementById('det-turno').innerText = datosProductoActual.turno;
            document.getElementById('det-fecha').innerText = datosProductoActual.fecha;
            document.getElementById('det-peso').innerText = datosProductoActual.peso;
            document.getElementById('det-conos').innerText = datosProductoActual.conos;
            document.getElementById('det-responsable').innerText = datosProductoActual.responsable;

            // Rellena automáticamente el campo con el peso de la etiqueta leída
            document.getElementById('cant-peso').value = datosProductoActual.peso;

            document.getElementById('res-box').style.display = 'block';
            cargarStock(datosProductoActual.titulo, datosProductoActual.tipo_rafia);
        }

        async function cargarStock(titulo, tipo_rafia) {
            let res = await fetch('/api/producto?titulo=' + encodeURIComponent(titulo) + '&tipo_rafia=' + encodeURIComponent(tipo_rafia));
            let data = await res.json();
            document.getElementById('p-stock').innerText = data.total_peso || 0;
        }

        async function registrar(tipo) {
            let pesoIngresado = parseFloat(document.getElementById('cant-peso').value) || 0;
            
            if (pesoIngresado <= 0) {
                alert("Por favor ingresa un peso válido mayor a 0 kg.");
                return;
            }

            let res = await fetch('/api/movimiento', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ 
                    datos: datosProductoActual,
                    tipo: tipo, 
                    peso: pesoIngresado 
                })
            });
            let data = await res.json();
            if (data.ok) {
                alert(`Movimiento de ${tipo.toUpperCase()} guardado (${pesoIngresado} kg).`);
                document.getElementById('res-box').style.display = 'none';
                actualizarTabla();
            }
        }

        async function actualizarTabla() {
            let res = await fetch('/api/inventario');
            let data = await res.json();
            let html = "";
            
            data.forEach((p, idx) => {
                let badgeTipo = p.tipo === 'entrada' 
                    ? '<span style="color:green; font-weight:bold;">+ Entrada</span>' 
                    : '<span style="color:red; font-weight:bold;">- Salida</span>';

                html += `<tr>
                    <td>${idx + 1}</td>
                    <td><b>${p.titulo}</b><br><small style="color:#2563eb;">(${p.tipo_rafia || 'N/A'})</small></td>
                    <td>${p.turno} | ${p.fecha}<br>Conos: ${p.conos} | Resp: ${p.responsable}</td>
                    <td>${badgeTipo}</td>
                    <td><b>${p.peso} kg</b></td>
                </tr>`;
            });
            
            document.getElementById('tabla-body').innerHTML = html;
        }

        function generarEtiqueta() {
            let titulo = document.getElementById('gen-titulo').value.trim();
            let tipoRafia = document.getElementById('gen-tipo-rafia').value;
            let turno = document.getElementById('gen-turno').value;
            let fecha = document.getElementById('gen-fecha').value;
            let peso = document.getElementById('gen-peso').value.trim();
            let conos = document.getElementById('gen-conos').value.trim();
            let responsable = document.getElementById('gen-responsable').value.trim();

            if (!titulo || !peso || !fecha || !conos || !responsable) {
                alert("Por favor completa todos los campos (incluyendo el peso).");
                return;
            }

            let codigoEstructurado = `${titulo}|${tipoRafia}|${turno}|${fecha}|${peso}|${conos}|${responsable}`;

            document.getElementById('lbl-nombre').innerText = `${titulo} (${tipoRafia}) - ${peso} kg`;
            document.getElementById('area-impresion').style.display = 'flex';
            document.getElementById('acciones-etiqueta').style.display = 'flex';

            const qrcodeContainer = document.getElementById('qrcode');
            qrcodeContainer.innerHTML = "";

            const qrElement = kjua({
                text: codigoEstructurado,
                size: 180,
                fill: '#000000',
                back: '#ffffff',
                render: 'image'
            });

            qrcodeContainer.appendChild(qrElement);
        }

        function guardarComoImagen() {
            const contenedor = document.getElementById('area-impresion');
            html2canvas(contenedor, { scale: 3, backgroundColor: "#ffffff" }).then(canvas => {
                const link = document.createElement('a');
                link.download = `Etiqueta_${document.getElementById('gen-titulo').value}_${document.getElementById('gen-tipo-rafia').value}.png`;
                link.href = canvas.toDataURL('image/png');
                link.click();
            });
        }

        modoCamara();
        actualizarTabla();
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/producto')
def get_producto():
    titulo = request.args.get('titulo', '')
    tipo_rafia = request.args.get('tipo_rafia', '')
    
    # Suma las entradas en kg y resta las salidas en kg
    total_peso = sum(
        item['peso'] if item['tipo'] == 'entrada' else -item['peso']
        for item in inventario_registros 
        if item['titulo'] == titulo and item.get('tipo_rafia') == tipo_rafia
    )
    return jsonify({"total_peso": round(total_peso, 2)})

@app.route('/api/movimiento', methods=['POST'])
def registrar_movimiento():
    req = request.json
    datos = req.get('datos', {})
    tipo = req.get('tipo')
    peso = float(req.get('peso', 0))
    
 