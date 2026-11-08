// ==UserScript==
// @name         NEOESTADO · rellena SERVIR y SEACE
// @namespace    https://github.com/RedyDelgado/cotizador
// @version      1.0.0
// @description  Al abrir un enlace de NEOESTADO, rellena el buscador de SERVIR (y lo ejecuta) o el de SEACE 3.0 (tú pulsas Buscar: tiene captcha).
// @author       NEOESTADO
// @match        https://app.servir.gob.pe/DifusionOfertasExterno/faces/consultas/ofertas_laborales.xhtml*
// @match        https://prod2.seace.gob.pe/seacebus-uiwd-pub/buscadorPublico/buscadorPublico.xhtml*
// @run-at       document-idle
// @grant        none
// @downloadURL  https://raw.githubusercontent.com/RedyDelgado/cotizador/main/userscripts/neoestado.user.js
// @updateURL    https://raw.githubusercontent.com/RedyDelgado/cotizador/main/userscripts/neoestado.user.js
// ==/UserScript==

/*
 * Los enlaces de los correos y de Telegram llevan al final lo que hay que buscar:
 *   SERVIR  ...ofertas_laborales.xhtml#conv=276-6&puesto=INGENIERO+CIVIL
 *                                                      -> escribe número y puesto (el número se repite entre entidades)
 *                                                         y pulsa «Buscar»: queda solo esa oferta
 *   SEACE   ...buscadorPublico.xhtml#seace=LP-ABR-22-2026-DEC-OC-MPLC/LC-1
 *                                                      -> rellena año, número y sigla; el captcha y «Buscar» son tuyos
 * Lo que va tras el # no se envía al servidor: sin este script el enlace abre el buscador normal.
 * No se envía ni se guarda nada: solo se rellenan campos de la página que tienes abierta.
 */
(function () {
    'use strict';

    const params = new URLSearchParams(location.hash.replace(/^#/, ''));
    const esServir = location.hostname === 'app.servir.gob.pe';
    const valor = esServir ? params.get('conv') : params.get('seace');
    if (!valor) return;

    const campo = id => document.getElementById(id);
    const pausa = ms => new Promise(r => setTimeout(r, ms));

    /** Espera a que la página (PrimeFaces) termine de armar el formulario. */
    async function esperar(comprobar, intentos = 40) {
        for (let i = 0; i < intentos; i++) {
            const r = comprobar();
            if (r) return r;
            await pausa(250);
        }
        return null;
    }

    function escribir(input, texto) {
        input.focus();
        input.value = texto;
        for (const tipo of ['input', 'keyup', 'change', 'blur']) input.dispatchEvent(new Event(tipo, { bubbles: true }));
    }

    function aviso(texto, color) {
        const caja = document.createElement('div');
        caja.textContent = texto;
        caja.setAttribute('role', 'status');
        caja.style.cssText = 'position:fixed;z-index:99999;left:50%;top:12px;transform:translateX(-50%);max-width:92vw;padding:10px 16px;'
            + 'border-radius:10px;font:600 14px/1.4 system-ui,sans-serif;color:#fff;box-shadow:0 6px 24px rgba(0,0,0,.3);background:' + (color || '#6D28D9');
        document.body.appendChild(caja);
        setTimeout(() => caja.remove(), 12000);
    }

    async function servir() {
        const nro = await esperar(() => campo('frmLstOfertsLabo:txtNroConv'));
        const buscar = await esperar(() => [...document.querySelectorAll('#frmLstOfertsLabo button')].find(b => b.textContent.trim() === 'Buscar'));
        if (!nro || !buscar) return aviso('NEOESTADO: no encontré el buscador de SERVIR (¿cambió la página?). Número de convocatoria: ' + valor, '#B91C1C');
        escribir(nro, valor);
        const puesto = params.get('puesto'), campoPuesto = campo('frmLstOfertsLabo:txtPuesto');
        if (puesto && campoPuesto) escribir(campoPuesto, puesto);
        aviso('NEOESTADO: buscando la convocatoria ' + valor + (params.get('puesto') ? ' · ' + params.get('puesto') : '') + '…');
        await pausa(300);
        buscar.click();
    }

    /** "LP-ABR-22-2026-DEC-OC-MPLC/LC-1" -> {numero: "22", anio: "2026", sigla: "DEC-OC-MPLC/LC-1"} (null si no tiene esa forma). */
    function partesDeNomenclatura(texto) {
        const m = texto.match(/^[A-Z]+(?:-[A-Z]+)?-(\d+)-(\d{4})-(.+)$/i);
        return m ? { numero: m[1], anio: m[2], sigla: m[3] } : null;
    }

    async function seace() {
        // el formulario está en la pestaña «Buscador de Procedimientos de Selección»: se abre primero
        const pestana = await esperar(() => [...document.querySelectorAll('.ui-tabs-nav a')].find(x => /Procedimientos de Selecci/.test(x.textContent)));
        if (pestana) { pestana.click(); await pausa(600); }
        const numero = await esperar(() => campo('tbBuscador:idFormBuscarProceso:numeroSeleccion'));
        if (!numero) return aviso('NEOESTADO: no encontré el buscador de SEACE (¿cambió la página?). Nomenclatura: ' + valor, '#B91C1C');
        const partes = partesDeNomenclatura(valor);
        if (partes) {
            escribir(numero, partes.numero);
            // la sigla está en «Búsqueda Avanzada», plegada: se despliega
            const avanzada = [...document.querySelectorAll('.ui-fieldset-legend')].find(x => /B.squeda Avanzada/.test(x.textContent));
            if (avanzada && !(campo('tbBuscador:idFormBuscarProceso:siglasEntidad') || {}).offsetParent) { avanzada.click(); await pausa(500); }
            const sigla = campo('tbBuscador:idFormBuscarProceso:siglasEntidad');
            if (sigla) escribir(sigla, partes.sigla);
            const anio = campo('tbBuscador:idFormBuscarProceso:anioConvocatoria_input'); // lista de PrimeFaces: select oculto + etiqueta
            if (anio && [...anio.options].some(o => o.value === partes.anio)) {
                anio.value = partes.anio;
                anio.dispatchEvent(new Event('change', { bubbles: true }));
                const etiqueta = campo('tbBuscador:idFormBuscarProceso:anioConvocatoria_label');
                if (etiqueta) etiqueta.textContent = partes.anio;
            }
        }
        aviso('NEOESTADO: ' + valor + (partes ? ' — completé año, número y sigla. Revisa y pulsa «Buscar» (el captcha lo resuelves tú).'
            : ' — cópialo en la búsqueda. El captcha y «Buscar» son tuyos.'));
    }

    (esServir ? servir : seace)();
})();
