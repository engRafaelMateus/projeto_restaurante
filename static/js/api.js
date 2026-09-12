/* ---------------------------------------------------------------------------
   Utilidades compartilhadas pelas telas de garçom e caixa.

   Duas decisões que valem a leitura:

   1. Nada é montado com innerHTML a partir de dado vindo do servidor. Todo
      texto entra por textContent, então o nome de um produto ou a observação
      "sem cebola <script>" aparece como texto, nunca como HTML.

   2. `requisitar` distingue três desfechos: resposta do servidor com sucesso,
      resposta com erro de negócio e falha de rede. O terceiro caso é o
      perigoso — o servidor pode ter gravado — e a interface precisa dizer
      isso ao usuário em vez de fingir que nada aconteceu.
   --------------------------------------------------------------------------- */
window.API = (function () {
    'use strict';

    function lerCookie(nome) {
        const partes = (document.cookie || '').split(';');
        for (const parte of partes) {
            const limpo = parte.trim();
            if (limpo.startsWith(nome + '=')) {
                return decodeURIComponent(limpo.substring(nome.length + 1));
            }
        }
        return null;
    }

    async function requisitar(url, opcoes) {
        const config = opcoes || {};
        const metodo = config.metodo || 'GET';
        const cabecalhos = {'X-Requested-With': 'fetch'};
        let corpo;

        if (config.corpo !== undefined && config.corpo !== null) {
            cabecalhos['Content-Type'] = 'application/json';
            corpo = JSON.stringify(config.corpo);
        }
        if (metodo !== 'GET' && metodo !== 'HEAD') {
            cabecalhos['X-CSRFToken'] = lerCookie('csrftoken') || '';
        }

        try {
            const resposta = await fetch(url, {
                method: metodo,
                headers: cabecalhos,
                body: corpo,
                credentials: 'same-origin',
            });

            let dados = null;
            try {
                dados = await resposta.json();
            } catch (erro) {
                dados = null;
            }

            if (resposta.status === 401) {
                return {
                    houveResposta: true,
                    ok: false,
                    status: 401,
                    dados: dados,
                    mensagem: 'Sua sessão expirou. Entre novamente para continuar.',
                };
            }

            return {
                houveResposta: true,
                ok: resposta.ok && (!dados || dados.ok !== false),
                status: resposta.status,
                dados: dados,
                mensagem: (dados && dados.erro) || (resposta.ok ? '' : 'Não foi possível concluir a operação.'),
                detalhes: (dados && dados.detalhes) || null,
                codigo: (dados && dados.codigo) || null,
            };
        } catch (erro) {
            // Falha de rede: NÃO sabemos se o servidor gravou.
            return {
                houveResposta: false,
                ok: false,
                status: 0,
                dados: null,
                mensagem: 'Falha de conexão. Não foi possível confirmar se a operação foi gravada.',
            };
        }
    }

    function criar(tag, opcoes) {
        const config = opcoes || {};
        const elemento = document.createElement(tag);
        if (config.classe) elemento.className = config.classe;
        if (config.texto !== undefined) elemento.textContent = config.texto;
        if (config.atributos) {
            for (const chave in config.atributos) {
                if (config.atributos[chave] !== null && config.atributos[chave] !== undefined) {
                    elemento.setAttribute(chave, config.atributos[chave]);
                }
            }
        }
        if (config.filhos) {
            config.filhos.forEach(function (filho) {
                if (filho) elemento.appendChild(filho);
            });
        }
        return elemento;
    }

    function formatarBRL(valor) {
        const numero = Number(valor || 0);
        return numero.toLocaleString('pt-BR', {
            style: 'currency',
            currency: 'BRL',
            minimumFractionDigits: 2,
        });
    }

    function mostrarAviso(container, tipo, texto, extras) {
        container.replaceChildren();
        if (!texto) return;
        const classes = {erro: 'aviso--erro', ok: 'aviso--ok', atencao: 'aviso--atencao', info: 'aviso--informativo'};
        const caixa = criar('div', {classe: 'aviso ' + (classes[tipo] || classes.info)});
        caixa.appendChild(criar('div', {texto: texto}));
        (extras || []).forEach(function (linha) {
            caixa.appendChild(criar('div', {classe: 'texto-suave', texto: '• ' + linha}));
        });
        container.appendChild(caixa);
    }

    function uuid() {
        if (window.crypto && typeof window.crypto.randomUUID === 'function') {
            return window.crypto.randomUUID();
        }
        // Reserva para navegadores sem randomUUID (contexto não seguro).
        const aleatorio = new Uint8Array(16);
        (window.crypto || {getRandomValues: function (a) {
            for (let i = 0; i < a.length; i++) a[i] = Math.floor(Math.random() * 256);
            return a;
        }}).getRandomValues(aleatorio);
        aleatorio[6] = (aleatorio[6] & 0x0f) | 0x40;
        aleatorio[8] = (aleatorio[8] & 0x3f) | 0x80;
        const hex = Array.from(aleatorio, function (b) {
            return b.toString(16).padStart(2, '0');
        }).join('');
        return (
            hex.slice(0, 8) + '-' + hex.slice(8, 12) + '-' + hex.slice(12, 16) + '-' +
            hex.slice(16, 20) + '-' + hex.slice(20)
        );
    }

    /* Armazenamento de rascunho por aba. Pode falhar (aba anônima, storage
       bloqueado), então toda leitura e escrita é protegida. */
    const rascunho = {
        ler: function (chave) {
            try {
                const bruto = window.sessionStorage.getItem(chave);
                return bruto ? JSON.parse(bruto) : null;
            } catch (erro) {
                return null;
            }
        },
        gravar: function (chave, valor) {
            try {
                window.sessionStorage.setItem(chave, JSON.stringify(valor));
            } catch (erro) {
                /* segue sem persistir */
            }
        },
        limpar: function (chave) {
            try {
                window.sessionStorage.removeItem(chave);
            } catch (erro) {
                /* segue */
            }
        },
    };

    return {
        requisitar: requisitar,
        criar: criar,
        formatarBRL: formatarBRL,
        mostrarAviso: mostrarAviso,
        uuid: uuid,
        rascunho: rascunho,
        lerCookie: lerCookie,
    };
})();
