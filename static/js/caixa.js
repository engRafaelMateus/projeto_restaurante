/* ---------------------------------------------------------------------------
   Painel do caixa.

   Atualização: polling HTTP simples a cada 10 segundos, suficiente para o
   volume de um salão e sem WebSocket, Redis ou fila. Duas regras protegem o
   operador:

   * enquanto um diálogo está aberto (pagamento ou motivo), o polling é
     suspenso — nada apaga o que ele está digitando;
   * falha de atualização aparece no indicador com botão de tentar de novo,
     em vez de a tela simplesmente congelar mostrando dado velho.
   --------------------------------------------------------------------------- */
(function () {
    'use strict';

    const permissoes = JSON.parse(document.getElementById('dados-caixa').textContent);
    const INTERVALO = 10000;

    const estado = {
        comanda: null,
        ocupadoEmDialogo: false,
        emOperacao: false,
        acaoDoMotivo: null,
    };

    const el = {
        indicador: document.getElementById('indicador'),
        gradeMesas: document.getElementById('grade-mesas'),
        mensagemGeral: document.getElementById('mensagem-geral'),
        painel: document.getElementById('painel-comanda'),
        tituloDetalhe: document.getElementById('titulo-detalhe'),
        identificacao: document.getElementById('identificacao-comanda'),
        mensagemComanda: document.getElementById('mensagem-comanda'),
        listaItens: document.getElementById('lista-itens-comanda'),
        semItens: document.getElementById('sem-itens'),
        totalComanda: document.getElementById('total-comanda'),
        botaoFecharPainel: document.getElementById('botao-fechar-painel'),
        botaoAtualizar: document.getElementById('botao-atualizar'),
        botaoAbrirPagamento: document.getElementById('botao-abrir-pagamento'),
        botaoCancelarComanda: document.getElementById('botao-cancelar-comanda'),

        dialogoPagamento: document.getElementById('dialogo-pagamento'),
        pagamentoMesa: document.getElementById('pagamento-mesa'),
        pagamentoComanda: document.getElementById('pagamento-comanda'),
        pagamentoTotal: document.getElementById('pagamento-total'),
        meioPagamento: document.getElementById('meio-pagamento'),
        blocoDinheiro: document.getElementById('bloco-dinheiro'),
        valorRecebido: document.getElementById('valor-recebido'),
        trocoPrevisto: document.getElementById('troco-previsto'),
        observacaoPagamento: document.getElementById('observacao-pagamento'),
        erroPagamento: document.getElementById('erro-pagamento'),
        botaoConfirmarPagamento: document.getElementById('botao-confirmar-pagamento'),
        botaoFecharPagamento: document.getElementById('botao-fechar-pagamento'),

        dialogoMotivo: document.getElementById('dialogo-motivo'),
        descricaoMotivo: document.getElementById('descricao-motivo'),
        textoMotivo: document.getElementById('texto-motivo'),
        erroMotivo: document.getElementById('erro-motivo'),
        botaoConfirmarMotivo: document.getElementById('botao-confirmar-motivo'),
        botaoFecharMotivo: document.getElementById('botao-fechar-motivo'),
    };

    /* --- indicador de atualização ------------------------------------------ */
    function indicar(tipo, texto, comBotao) {
        el.indicador.replaceChildren();
        const classe = tipo === 'falha' ? 'ponto ponto--falha'
            : tipo === 'carregando' ? 'ponto ponto--carregando' : 'ponto';
        el.indicador.appendChild(API.criar('span', {classe: classe}));
        el.indicador.appendChild(document.createTextNode(' ' + texto));
        if (comBotao) {
            const botao = API.criar('button', {
                classe: 'botao botao--pequeno',
                texto: 'Tentar de novo',
                atributos: {type: 'button'},
            });
            botao.addEventListener('click', atualizarSalao);
            el.indicador.appendChild(botao);
        }
    }

    /* --- mesas -------------------------------------------------------------- */
    async function atualizarSalao() {
        if (estado.ocupadoEmDialogo) return;
        const resultado = await API.requisitar('/atendimento/api/estado/');

        if (!resultado.ok) {
            indicar('falha', 'atualização falhou — os dados podem estar desatualizados.', true);
            return;
        }
        indicar('ok', 'atualizado às ' + new Date().toLocaleTimeString('pt-BR'));

        const porNumero = {};
        resultado.dados.mesas.forEach(function (mesa) { porNumero[mesa.numero] = mesa; });

        Array.prototype.forEach.call(el.gradeMesas ? el.gradeMesas.children : [], function (botao) {
            const info = porNumero[Number(botao.dataset.mesa)];
            const etiqueta = botao.querySelector('[data-papel="situacao"]');
            const total = botao.querySelector('[data-papel="total"]');
            const itens = botao.querySelector('[data-papel="itens"]');
            const ocupada = info && info.ocupada;

            botao.classList.toggle('mesa--ocupada', !!ocupada);
            botao.classList.toggle('mesa--livre', !ocupada);
            botao.dataset.comanda = ocupada ? info.comanda_id : '';
            etiqueta.className = 'etiqueta ' + (ocupada ? 'etiqueta--ocupada' : 'etiqueta--livre');
            etiqueta.textContent = ocupada ? '● Ocupada' : '● Livre';
            total.textContent = ocupada ? info.total_formatado : '';
            itens.textContent = ocupada
                ? info.itens + ' item(ns)' + (info.aberta_por ? ' · ' + info.aberta_por : '')
                : '';
        });

        // Mantém o painel aberto em dia com o servidor.
        if (estado.comanda) await recarregarComanda(true);
    }

    /* --- painel da comanda -------------------------------------------------- */
    async function abrirComanda(numeroDaMesa) {
        el.mensagemComanda.replaceChildren();
        const resultado = await API.requisitar(
            '/atendimento/api/mesas/' + numeroDaMesa + '/comanda/'
        );

        if (!resultado.ok) {
            API.mostrarAviso(el.mensagemGeral, 'erro', resultado.mensagem);
            return;
        }

        if (!resultado.dados.comanda) {
            estado.comanda = null;
            el.painel.hidden = false;
            el.tituloDetalhe.textContent = 'Mesa ' + numeroDaMesa;
            el.identificacao.textContent = 'Mesa livre: nenhuma comanda aberta.';
            el.listaItens.replaceChildren();
            el.semItens.hidden = true;
            el.totalComanda.textContent = API.formatarBRL(0);
            if (el.botaoAbrirPagamento) el.botaoAbrirPagamento.disabled = true;
            if (el.botaoCancelarComanda) el.botaoCancelarComanda.disabled = true;
            el.painel.scrollIntoView({behavior: 'smooth', block: 'start'});
            return;
        }

        estado.comanda = resultado.dados.comanda;
        desenharComanda();
        el.painel.scrollIntoView({behavior: 'smooth', block: 'start'});
    }

    async function recarregarComanda(silencioso) {
        if (!estado.comanda) return;
        const resultado = await API.requisitar('/atendimento/api/comandas/' + estado.comanda.id + '/');
        if (!resultado.ok) {
            if (!silencioso) API.mostrarAviso(el.mensagemComanda, 'erro', resultado.mensagem);
            return;
        }
        estado.comanda = resultado.dados.comanda;
        desenharComanda();
    }

    function desenharComanda() {
        const comanda = estado.comanda;
        el.painel.hidden = false;
        el.tituloDetalhe.textContent = 'Mesa ' + comanda.mesa + ' · comanda #' + comanda.id;

        const encerrada = comanda.status !== 'aberta';
        el.identificacao.textContent =
            'Aberta em ' + new Date(comanda.aberta_em).toLocaleString('pt-BR') +
            (comanda.aberta_por ? ' por ' + comanda.aberta_por : '') +
            ' · situação: ' + comanda.status_exibicao;

        const ativos = comanda.itens.filter(function (item) { return !item.cancelado; });
        el.semItens.hidden = ativos.length > 0;
        el.listaItens.replaceChildren();

        comanda.itens.forEach(function (item) {
            const detalhes = [];
            if (item.adicionais && item.adicionais.length) {
                detalhes.push('+ ' + item.adicionais.map(function (a) { return a.nome; }).join(', '));
            }
            if (item.observacao) detalhes.push('Obs.: ' + item.observacao);
            if (item.lancado_por) detalhes.push('Lançado por ' + item.lancado_por);
            if (item.cancelado) {
                detalhes.push('CANCELADO — ' + item.motivo_cancelamento);
            }

            const blocoTexto = API.criar('div', {
                filhos: [API.criar('div', {
                    classe: 'descricao negrito',
                    texto: item.quantidade + 'x ' + item.descricao,
                })].concat(
                    detalhes.map(function (linha) {
                        return API.criar('div', {classe: 'texto-suave', texto: linha});
                    })
                ),
            });

            const lado = API.criar('div', {classe: 'texto-direita'});
            lado.appendChild(API.criar('div', {classe: 'valor', texto: item.subtotal_formatado}));

            if (permissoes.podeCancelarItem && !item.cancelado && !encerrada) {
                const botao = API.criar('button', {
                    classe: 'botao botao--pequeno',
                    texto: 'Cancelar item',
                    atributos: {type: 'button', 'aria-label': 'Cancelar ' + item.descricao},
                });
                botao.addEventListener('click', function () {
                    pedirMotivo(
                        'Cancelar "' + item.quantidade + 'x ' + item.descricao + '" da comanda #' + comanda.id + '.',
                        function (motivo) { return cancelarItem(item.id, motivo); }
                    );
                });
                lado.appendChild(botao);
            }

            el.listaItens.appendChild(
                API.criar('li', {
                    classe: item.cancelado ? 'item-cancelado' : '',
                    filhos: [blocoTexto, lado],
                })
            );
        });

        el.totalComanda.textContent = comanda.total_formatado;

        if (el.botaoAbrirPagamento) {
            el.botaoAbrirPagamento.disabled = encerrada || Number(comanda.total) <= 0 || estado.emOperacao;
        }
        if (el.botaoCancelarComanda) {
            el.botaoCancelarComanda.disabled = encerrada || ativos.length > 0 || estado.emOperacao;
        }

        if (encerrada) {
            API.mostrarAviso(
                el.mensagemComanda,
                'ok',
                'Comanda ' + comanda.status_exibicao.toLowerCase() + '. A mesa está livre para um novo atendimento.'
            );
        }
    }

    function fecharPainel() {
        estado.comanda = null;
        el.painel.hidden = true;
        el.mensagemComanda.replaceChildren();
    }

    /* --- cancelamento com motivo -------------------------------------------- */
    function pedirMotivo(descricao, acao) {
        estado.acaoDoMotivo = acao;
        el.descricaoMotivo.textContent = descricao;
        el.textoMotivo.value = '';
        el.erroMotivo.replaceChildren();
        estado.ocupadoEmDialogo = true;
        el.dialogoMotivo.showModal();
        el.textoMotivo.focus();
    }

    async function confirmarMotivo() {
        const motivo = el.textoMotivo.value.trim();
        if (motivo.length < 3) {
            API.mostrarAviso(el.erroMotivo, 'erro', 'Descreva o motivo com pelo menos 3 caracteres.');
            return;
        }
        el.botaoConfirmarMotivo.disabled = true;
        el.botaoConfirmarMotivo.textContent = 'Confirmando…';

        const resultado = await estado.acaoDoMotivo(motivo);

        el.botaoConfirmarMotivo.disabled = false;
        el.botaoConfirmarMotivo.textContent = 'Confirmar';

        if (resultado && resultado.ok) {
            el.dialogoMotivo.close();
        } else if (resultado) {
            API.mostrarAviso(el.erroMotivo, 'erro', resultado.mensagem);
        }
    }

    async function cancelarItem(itemId, motivo) {
        const resultado = await API.requisitar('/atendimento/api/itens/' + itemId + '/cancelar/', {
            metodo: 'POST',
            corpo: {motivo: motivo},
        });
        if (resultado.ok) {
            estado.comanda = resultado.dados.comanda;
            desenharComanda();
            API.mostrarAviso(el.mensagemComanda, 'ok', 'Item cancelado. Total corrigido para ' +
                estado.comanda.total_formatado + '.');
            atualizarSalao();
        }
        return resultado;
    }

    async function cancelarComanda(motivo) {
        const resultado = await API.requisitar(
            '/atendimento/api/comandas/' + estado.comanda.id + '/cancelar/',
            {metodo: 'POST', corpo: {motivo: motivo}}
        );
        if (resultado.ok) {
            estado.comanda = resultado.dados.comanda;
            desenharComanda();
            API.mostrarAviso(el.mensagemComanda, 'ok', 'Comanda cancelada sem registrar venda. Mesa liberada.');
            atualizarSalao();
        }
        return resultado;
    }

    /* --- pagamento ---------------------------------------------------------- */
    function abrirPagamento() {
        if (!estado.comanda) return;
        el.pagamentoMesa.textContent = String(estado.comanda.mesa);
        el.pagamentoComanda.textContent = '#' + estado.comanda.id;
        el.pagamentoTotal.textContent = estado.comanda.total_formatado;
        el.meioPagamento.value = 'dinheiro';
        el.valorRecebido.value = '';
        el.observacaoPagamento.value = '';
        el.erroPagamento.replaceChildren();
        atualizarBlocoDinheiro();
        estado.ocupadoEmDialogo = true;
        el.dialogoPagamento.showModal();
        el.meioPagamento.focus();
    }

    function atualizarBlocoDinheiro() {
        const emDinheiro = el.meioPagamento.value === 'dinheiro';
        el.blocoDinheiro.hidden = !emDinheiro;
        atualizarTroco();
    }

    function atualizarTroco() {
        if (!estado.comanda) return;
        const total = Number(estado.comanda.total);
        const recebido = Number(el.valorRecebido.value || 0);
        const troco = recebido - total;
        el.trocoPrevisto.textContent = troco >= 0
            ? API.formatarBRL(troco)
            : 'falta ' + API.formatarBRL(Math.abs(troco));
    }

    async function confirmarPagamento() {
        if (estado.emOperacao || !estado.comanda) return;
        estado.emOperacao = true;
        el.botaoConfirmarPagamento.disabled = true;
        el.botaoConfirmarPagamento.textContent = 'Registrando…';
        el.erroPagamento.replaceChildren();

        const corpo = {
            meio: el.meioPagamento.value,
            observacao: el.observacaoPagamento.value.trim(),
        };
        if (el.meioPagamento.value === 'dinheiro') {
            corpo.valor_recebido = el.valorRecebido.value;
        }

        const resultado = await API.requisitar(
            '/atendimento/api/comandas/' + estado.comanda.id + '/pagamento/',
            {metodo: 'POST', corpo: corpo}
        );

        estado.emOperacao = false;
        el.botaoConfirmarPagamento.disabled = false;
        el.botaoConfirmarPagamento.textContent = 'Confirmar pagamento';

        if (resultado.ok) {
            const pagamento = resultado.dados.pagamento;
            estado.comanda = resultado.dados.comanda;
            fecharDialogo(el.dialogoPagamento);
            desenharComanda();

            let texto = 'Pagamento de ' + pagamento.valor_formatado + ' registrado (' +
                pagamento.meio_exibicao + '). Comanda encerrada e mesa liberada.';
            if (pagamento.troco_formatado) {
                texto += ' Troco: ' + pagamento.troco_formatado + '.';
            }
            API.mostrarAviso(el.mensagemGeral, 'ok', texto);
            atualizarSalao();
            return;
        }

        if (!resultado.houveResposta) {
            API.mostrarAviso(
                el.erroPagamento,
                'atencao',
                'A conexão falhou e não dá para saber se o pagamento foi gravado. ' +
                'Feche esta janela e confira a situação da comanda antes de registrar de novo.'
            );
            return;
        }
        API.mostrarAviso(el.erroPagamento, 'erro', resultado.mensagem);
        if (resultado.codigo === 'pagamento_duplicado' || resultado.codigo === 'comanda_encerrada') {
            recarregarComanda(true);
        }
    }

    function fecharDialogo(dialogo) {
        dialogo.close();
        estado.ocupadoEmDialogo = false;
    }

    /* --- ligações ----------------------------------------------------------- */
    if (el.gradeMesas) {
        el.gradeMesas.addEventListener('click', function (evento) {
            const botao = evento.target.closest('.mesa');
            if (botao) abrirComanda(Number(botao.dataset.mesa));
        });
    }

    el.botaoFecharPainel.addEventListener('click', fecharPainel);
    el.botaoAtualizar.addEventListener('click', atualizarSalao);

    if (el.botaoAbrirPagamento) {
        el.botaoAbrirPagamento.addEventListener('click', abrirPagamento);
    }
    if (el.botaoCancelarComanda) {
        el.botaoCancelarComanda.addEventListener('click', function () {
            pedirMotivo(
                'Cancelar a comanda #' + estado.comanda.id + ' da mesa ' + estado.comanda.mesa +
                ' sem registrar venda.',
                cancelarComanda
            );
        });
    }

    el.meioPagamento.addEventListener('change', atualizarBlocoDinheiro);
    el.valorRecebido.addEventListener('input', atualizarTroco);
    el.botaoConfirmarPagamento.addEventListener('click', confirmarPagamento);
    el.botaoFecharPagamento.addEventListener('click', function () { fecharDialogo(el.dialogoPagamento); });
    el.dialogoPagamento.addEventListener('close', function () { estado.ocupadoEmDialogo = false; });

    el.botaoConfirmarMotivo.addEventListener('click', confirmarMotivo);
    el.botaoFecharMotivo.addEventListener('click', function () { fecharDialogo(el.dialogoMotivo); });
    el.dialogoMotivo.addEventListener('close', function () { estado.ocupadoEmDialogo = false; });

    atualizarSalao();
    window.setInterval(atualizarSalao, INTERVALO);
})();
