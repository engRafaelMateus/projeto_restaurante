/* ---------------------------------------------------------------------------
   Tela do garçom.

   Fluxo: escolher mesa -> abrir/recuperar comanda -> montar rascunho local ->
   enviar o rascunho inteiro em um POST idempotente.

   Idempotência: a referência do envio (UUID) é gerada quando o rascunho ganha
   o primeiro item e só é descartada quando o servidor confirma a gravação. Se
   o envio falhar por rede, o botão "Tentar novamente" reenvia **a mesma**
   referência — se o servidor já tinha gravado, ele devolve o mesmo resultado
   e nada duplica.
   --------------------------------------------------------------------------- */
(function () {
    'use strict';

    const configuracao = JSON.parse(document.getElementById('dados-comanda').textContent);
    const QUANTIDADE_MAXIMA = configuracao.quantidadeMaxima || 99;

    const estado = {
        catalogo: null,
        mesa: null,
        comanda: null,      // resumo vindo do servidor
        rascunho: [],       // itens ainda não enviados
        referenciaEnvio: null,
        enviando: false,
        selecao: null,      // item sendo montado no diálogo
    };

    const el = {
        gradeMesas: document.getElementById('grade-mesas'),
        indicadorMesas: document.getElementById('indicador-mesas'),
        secaoMesa: document.getElementById('secao-mesa'),
        secaoComanda: document.getElementById('secao-comanda'),
        rotuloMesa: document.getElementById('rotulo-mesa'),
        identificacao: document.getElementById('identificacao-comanda'),
        mensagem: document.getElementById('mensagem-comanda'),
        categorias: document.getElementById('categorias'),
        itensEnviados: document.getElementById('itens-enviados'),
        semEnviados: document.getElementById('sem-itens-enviados'),
        itensRascunho: document.getElementById('itens-rascunho'),
        semRascunho: document.getElementById('sem-rascunho'),
        barraEnvio: document.getElementById('barra-envio'),
        totalGeral: document.getElementById('total-geral'),
        detalheTotal: document.getElementById('detalhe-total'),
        botaoEnviar: document.getElementById('botao-enviar'),
        botaoTrocarMesa: document.getElementById('botao-trocar-mesa'),
        dialogo: document.getElementById('dialogo-item'),
        busca: document.getElementById('busca-produto'),
        listaProdutos: document.getElementById('lista-produtos'),
        blocoMeio: document.getElementById('bloco-meio-a-meio'),
        explicacaoMeio: document.getElementById('explicacao-meio-a-meio'),
        listaSegundoSabor: document.getElementById('lista-segundo-sabor'),
        blocoAdicionais: document.getElementById('bloco-adicionais'),
        listaAdicionais: document.getElementById('lista-adicionais'),
        quantidade: document.getElementById('quantidade-item'),
        subtotalItem: document.getElementById('subtotal-item'),
        observacao: document.getElementById('observacao-item'),
        contadorObservacao: document.getElementById('contador-observacao'),
        erroDialogo: document.getElementById('erro-dialogo'),
        botaoMenos: document.getElementById('botao-menos'),
        botaoMais: document.getElementById('botao-mais'),
        botaoAdicionar: document.getElementById('botao-adicionar-rascunho'),
        botaoCancelarItem: document.getElementById('botao-cancelar-item'),
    };

    function chaveDoRascunho() {
        return 'rascunho-comanda-' + (estado.comanda ? estado.comanda.id : 'nenhuma');
    }

    function salvarRascunho() {
        if (!estado.comanda) return;
        API.rascunho.gravar(chaveDoRascunho(), {
            itens: estado.rascunho,
            referenciaEnvio: estado.referenciaEnvio,
        });
    }

    function restaurarRascunho() {
        const salvo = API.rascunho.ler(chaveDoRascunho());
        estado.rascunho = (salvo && salvo.itens) || [];
        estado.referenciaEnvio = (salvo && salvo.referenciaEnvio) || null;
    }

    /* --- estado do salão --------------------------------------------------- */
    async function atualizarMesas() {
        const resultado = await API.requisitar('/atendimento/api/estado/');
        if (!resultado.ok) {
            el.indicadorMesas.replaceChildren(
                API.criar('span', {classe: 'ponto ponto--falha'}),
                document.createTextNode(' não foi possível atualizar as mesas')
            );
            return;
        }
        el.indicadorMesas.replaceChildren(
            API.criar('span', {classe: 'ponto'}),
            document.createTextNode(' mesas atualizadas')
        );

        const porNumero = {};
        resultado.dados.mesas.forEach(function (mesa) {
            porNumero[mesa.numero] = mesa;
        });

        Array.prototype.forEach.call(el.gradeMesas ? el.gradeMesas.children : [], function (botao) {
            const info = porNumero[Number(botao.dataset.mesa)];
            const etiqueta = botao.querySelector('[data-papel="situacao"]');
            const total = botao.querySelector('[data-papel="total"]');
            const ocupada = info && info.ocupada;

            botao.classList.toggle('mesa--ocupada', !!ocupada);
            botao.classList.toggle('mesa--livre', !ocupada);
            etiqueta.className = 'etiqueta ' + (ocupada ? 'etiqueta--ocupada' : 'etiqueta--livre');
            etiqueta.textContent = ocupada ? '● Ocupada' : '● Livre';
            total.textContent = ocupada ? info.total_formatado : '';
        });
    }

    /* --- abrir mesa -------------------------------------------------------- */
    async function abrirMesa(numero) {
        API.mostrarAviso(el.mensagem, 'info', 'Abrindo a mesa ' + numero + '…');
        const resultado = await API.requisitar('/atendimento/api/comandas/abrir/', {
            metodo: 'POST',
            corpo: {mesa: numero},
        });

        if (!resultado.ok) {
            API.mostrarAviso(el.mensagem, 'erro', resultado.mensagem);
            return;
        }

        estado.mesa = numero;
        estado.comanda = resultado.dados.comanda;
        restaurarRascunho();

        el.secaoMesa.hidden = true;
        el.secaoComanda.hidden = false;
        el.barraEnvio.hidden = false;
        el.rotuloMesa.textContent = 'mesa ' + numero;
        el.identificacao.textContent =
            'Comanda #' + estado.comanda.id + ' · aberta em ' +
            new Date(estado.comanda.aberta_em).toLocaleString('pt-BR') +
            (estado.comanda.aberta_por ? ' por ' + estado.comanda.aberta_por : '');

        API.mostrarAviso(
            el.mensagem,
            resultado.dados.criada ? 'ok' : 'info',
            resultado.dados.criada
                ? 'Comanda aberta para a mesa ' + numero + '.'
                : 'Comanda já estava aberta nesta mesa. Os itens abaixo já estão no servidor.'
        );

        await carregarCatalogo();
        desenharTudo();
    }

    function voltarParaMesas() {
        estado.mesa = null;
        estado.comanda = null;
        estado.rascunho = [];
        estado.referenciaEnvio = null;
        el.secaoComanda.hidden = true;
        el.barraEnvio.hidden = true;
        el.secaoMesa.hidden = false;
        el.mensagem.replaceChildren();
        atualizarMesas();
    }

    /* --- catálogo ---------------------------------------------------------- */
    async function carregarCatalogo() {
        if (estado.catalogo) return;
        const resultado = await API.requisitar('/atendimento/api/catalogo/');
        if (!resultado.ok) {
            API.mostrarAviso(el.mensagem, 'erro', 'Não foi possível carregar o cardápio. ' + resultado.mensagem);
            return;
        }
        estado.catalogo = resultado.dados.categorias;
        desenharCategorias();
    }

    function desenharCategorias() {
        el.categorias.replaceChildren();
        if (!estado.catalogo || !estado.catalogo.length) {
            el.categorias.appendChild(
                API.criar('p', {classe: 'texto-suave', texto: 'Nenhum produto disponível no cardápio.'})
            );
            return;
        }
        estado.catalogo.forEach(function (categoria) {
            const botao = API.criar('button', {
                classe: 'botao',
                texto: categoria.nome,
                atributos: {type: 'button'},
            });
            botao.addEventListener('click', function () {
                abrirDialogo(categoria);
            });
            el.categorias.appendChild(botao);
        });
    }

    /* --- diálogo de item --------------------------------------------------- */
    function abrirDialogo(categoria) {
        estado.selecao = {
            categoria: categoria,
            produto: null,
            produtoSecundario: null,
            adicionais: [],
        };
        el.busca.value = '';
        el.quantidade.value = 1;
        el.observacao.value = '';
        el.erroDialogo.replaceChildren();
        atualizarContadorObservacao();
        desenharProdutos();
        desenharAdicionais();
        el.blocoMeio.hidden = true;
        el.listaSegundoSabor.replaceChildren();
        atualizarSubtotalDoItem();
        document.getElementById('titulo-dialogo').textContent = categoria.nome;
        el.dialogo.showModal();
        el.busca.focus();
    }

    function desenharProdutos() {
        const termo = el.busca.value.trim().toLowerCase();
        el.listaProdutos.replaceChildren();

        const visiveis = estado.selecao.categoria.produtos.filter(function (produto) {
            return !termo || produto.nome.toLowerCase().indexOf(termo) !== -1;
        });

        if (!visiveis.length) {
            el.listaProdutos.appendChild(
                API.criar('p', {classe: 'texto-suave', texto: 'Nenhum produto encontrado com esse nome.'})
            );
            return;
        }

        visiveis.forEach(function (produto) {
            el.listaProdutos.appendChild(
                linhaDeOpcao(produto, 'radio', 'produto-principal', function () {
                    estado.selecao.produto = produto;
                    estado.selecao.produtoSecundario = null;
                    marcarSelecionado(el.listaProdutos, produto.id);
                    prepararMeioAMeio(produto);
                    atualizarSubtotalDoItem();
                })
            );
        });

        if (estado.selecao.produto) {
            marcarSelecionado(el.listaProdutos, estado.selecao.produto.id);
            const entrada = el.listaProdutos.querySelector(
                '.opcao[data-id="' + estado.selecao.produto.id + '"] input'
            );
            if (entrada) entrada.checked = true;
        }
    }

    function linhaDeOpcao(item, tipo, grupo, aoSelecionar, marcado) {
        const entrada = API.criar('input', {
            atributos: {type: tipo, name: grupo, value: String(item.id)},
        });
        entrada.checked = !!marcado;

        const texto = API.criar('span', {
            classe: 'opcao__texto',
            filhos: [
                API.criar('span', {classe: 'opcao__nome', texto: item.nome}),
                item.descricao
                    ? API.criar('span', {classe: 'texto-suave', texto: ' — ' + item.descricao})
                    : null,
            ],
        });

        const rotulo = API.criar('label', {
            classe: 'opcao',
            atributos: {'data-id': String(item.id)},
            filhos: [
                entrada,
                texto,
                API.criar('span', {classe: 'opcao__preco', texto: item.preco_formatado}),
            ],
        });

        entrada.addEventListener('change', aoSelecionar);
        return rotulo;
    }

    function marcarSelecionado(container, id) {
        Array.prototype.forEach.call(container.querySelectorAll('.opcao'), function (linha) {
            linha.classList.toggle('opcao--marcada', linha.dataset.id === String(id));
        });
    }

    function prepararMeioAMeio(produto) {
        const outros = estado.selecao.categoria.produtos.filter(function (p) {
            return p.meio_a_meio && p.id !== produto.id;
        });

        if (!produto.meio_a_meio || !outros.length) {
            el.blocoMeio.hidden = true;
            el.listaSegundoSabor.replaceChildren();
            return;
        }

        el.blocoMeio.hidden = false;
        el.explicacaoMeio.textContent =
            'Opcional. Com dois sabores, o servidor cobra o sabor mais caro.';
        el.listaSegundoSabor.replaceChildren();

        const nenhum = API.criar('button', {
            classe: 'botao botao--pequeno',
            texto: 'Sabor inteiro (sem segundo sabor)',
            atributos: {type: 'button'},
        });
        nenhum.addEventListener('click', function () {
            estado.selecao.produtoSecundario = null;
            marcarSelecionado(el.listaSegundoSabor, -1);
            atualizarSubtotalDoItem();
        });
        el.listaSegundoSabor.appendChild(nenhum);

        outros.forEach(function (outro) {
            el.listaSegundoSabor.appendChild(
                linhaDeOpcao(outro, 'radio', 'produto-secundario', function () {
                    estado.selecao.produtoSecundario = outro;
                    marcarSelecionado(el.listaSegundoSabor, outro.id);
                    atualizarSubtotalDoItem();
                })
            );
        });
    }

    function desenharAdicionais() {
        const adicionais = estado.selecao.categoria.adicionais || [];
        el.listaAdicionais.replaceChildren();
        el.blocoAdicionais.hidden = adicionais.length === 0;

        adicionais.forEach(function (adicional) {
            el.listaAdicionais.appendChild(
                linhaDeOpcao(adicional, 'checkbox', 'adicional-' + adicional.id, function (evento) {
                    if (evento.target.checked) {
                        estado.selecao.adicionais.push(adicional);
                    } else {
                        estado.selecao.adicionais = estado.selecao.adicionais.filter(function (a) {
                            return a.id !== adicional.id;
                        });
                    }
                    evento.target.closest('.opcao').classList.toggle('opcao--marcada', evento.target.checked);
                    atualizarSubtotalDoItem();
                })
            );
        });
    }

    function precoUnitarioPrevisto() {
        const selecao = estado.selecao;
        if (!selecao || !selecao.produto) return 0;
        let base = Number(selecao.produto.preco);
        if (selecao.produtoSecundario) {
            // Espelha a regra do servidor (maior valor). O valor oficial é
            // sempre o que o servidor devolve depois do envio.
            base = Math.max(base, Number(selecao.produtoSecundario.preco));
        }
        const adicionais = selecao.adicionais.reduce(function (soma, a) {
            return soma + Number(a.preco);
        }, 0);
        return base + adicionais;
    }

    function quantidadeValida() {
        let valor = parseInt(el.quantidade.value, 10);
        if (isNaN(valor) || valor < 1) valor = 1;
        if (valor > QUANTIDADE_MAXIMA) valor = QUANTIDADE_MAXIMA;
        return valor;
    }

    function atualizarSubtotalDoItem() {
        el.subtotalItem.textContent = API.formatarBRL(precoUnitarioPrevisto() * quantidadeValida());
    }

    function atualizarContadorObservacao() {
        const restantes = 140 - el.observacao.value.length;
        el.contadorObservacao.textContent = restantes + ' caracteres restantes';
    }

    function adicionarAoRascunho() {
        const selecao = estado.selecao;
        if (!selecao || !selecao.produto) {
            API.mostrarAviso(el.erroDialogo, 'erro', 'Escolha um produto antes de adicionar.');
            return;
        }

        const quantidade = quantidadeValida();
        const nome = selecao.produtoSecundario
            ? 'Meio a meio: ' + selecao.produto.nome + ' / ' + selecao.produtoSecundario.nome
            : selecao.produto.nome;

        estado.rascunho.push({
            produto_id: selecao.produto.id,
            produto_secundario_id: selecao.produtoSecundario ? selecao.produtoSecundario.id : null,
            quantidade: quantidade,
            observacao: el.observacao.value.trim(),
            adicionais: selecao.adicionais.map(function (a) { return a.id; }),
            // apenas para exibir o rascunho; o servidor recalcula tudo
            _nome: nome,
            _adicionais: selecao.adicionais.map(function (a) { return a.nome; }),
            _precoPrevisto: precoUnitarioPrevisto(),
        });

        if (!estado.referenciaEnvio) {
            estado.referenciaEnvio = API.uuid();
        }
        salvarRascunho();
        el.dialogo.close();
        desenharTudo();
    }

    /* --- desenho ----------------------------------------------------------- */
    function desenharTudo() {
        desenharEnviados();
        desenharRascunho();
        atualizarTotais();
    }

    function desenharEnviados() {
        el.itensEnviados.replaceChildren();
        const itens = (estado.comanda && estado.comanda.itens) || [];
        el.semEnviados.hidden = itens.length > 0;

        itens.forEach(function (item) {
            const descricao = API.criar('div', {
                filhos: [
                    API.criar('div', {
                        classe: 'descricao',
                        texto: item.quantidade + 'x ' + item.descricao,
                    }),
                    item.adicionais && item.adicionais.length
                        ? API.criar('div', {
                              classe: 'texto-suave',
                              texto: '+ ' + item.adicionais.map(function (a) { return a.nome; }).join(', '),
                          })
                        : null,
                    item.observacao
                        ? API.criar('div', {classe: 'texto-suave', texto: 'Obs.: ' + item.observacao})
                        : null,
                    item.cancelado
                        ? API.criar('div', {
                              classe: 'texto-suave',
                              texto: 'Cancelado — ' + item.motivo_cancelamento,
                          })
                        : null,
                ],
            });

            const linha = API.criar('li', {
                classe: item.cancelado ? 'item-cancelado' : '',
                filhos: [
                    descricao,
                    API.criar('span', {classe: 'valor', texto: item.subtotal_formatado}),
                ],
            });
            el.itensEnviados.appendChild(linha);
        });
    }

    function desenharRascunho() {
        el.itensRascunho.replaceChildren();
        el.semRascunho.hidden = estado.rascunho.length > 0;

        estado.rascunho.forEach(function (item, indice) {
            const remover = API.criar('button', {
                classe: 'botao botao--pequeno',
                texto: 'Remover',
                atributos: {type: 'button', 'aria-label': 'Remover ' + item._nome + ' do rascunho'},
            });
            remover.addEventListener('click', function () {
                estado.rascunho.splice(indice, 1);
                if (!estado.rascunho.length) estado.referenciaEnvio = null;
                salvarRascunho();
                desenharTudo();
            });

            const descricao = API.criar('div', {
                filhos: [
                    API.criar('div', {texto: item.quantidade + 'x ' + item._nome}),
                    item._adicionais.length
                        ? API.criar('div', {classe: 'texto-suave', texto: '+ ' + item._adicionais.join(', ')})
                        : null,
                    item.observacao
                        ? API.criar('div', {classe: 'texto-suave', texto: 'Obs.: ' + item.observacao})
                        : null,
                ],
            });

            el.itensRascunho.appendChild(
                API.criar('li', {
                    filhos: [
                        descricao,
                        API.criar('div', {
                            classe: 'texto-direita',
                            filhos: [
                                API.criar('div', {
                                    classe: 'valor',
                                    texto: API.formatarBRL(item._precoPrevisto * item.quantidade),
                                }),
                                remover,
                            ],
                        }),
                    ],
                })
            );
        });
    }

    function atualizarTotais() {
        const totalServidor = estado.comanda ? Number(estado.comanda.total) : 0;
        const totalRascunho = estado.rascunho.reduce(function (soma, item) {
            return soma + item._precoPrevisto * item.quantidade;
        }, 0);

        el.totalGeral.textContent = API.formatarBRL(totalServidor + totalRascunho);
        el.detalheTotal.textContent =
            'Confirmado no servidor: ' + API.formatarBRL(totalServidor) +
            ' · rascunho: ' + API.formatarBRL(totalRascunho) +
            (totalRascunho ? ' (valor final calculado pelo servidor no envio)' : '');

        el.botaoEnviar.disabled = estado.enviando || estado.rascunho.length === 0;
        el.botaoEnviar.textContent = estado.enviando
            ? 'Enviando…'
            : 'Enviar pedido' + (estado.rascunho.length ? ' (' + estado.rascunho.length + ' itens)' : '');
    }

    /* --- envio ------------------------------------------------------------- */
    async function enviarPedido() {
        if (estado.enviando || !estado.rascunho.length || !estado.comanda) return;

        estado.enviando = true;
        atualizarTotais();
        API.mostrarAviso(el.mensagem, 'info', 'Enviando o pedido ao servidor…');

        const corpo = {
            referencia_envio: estado.referenciaEnvio,
            itens: estado.rascunho.map(function (item) {
                return {
                    produto_id: item.produto_id,
                    produto_secundario_id: item.produto_secundario_id,
                    quantidade: item.quantidade,
                    observacao: item.observacao,
                    adicionais: item.adicionais,
                };
            }),
        };

        const resultado = await API.requisitar(
            '/atendimento/api/comandas/' + estado.comanda.id + '/itens/',
            {metodo: 'POST', corpo: corpo}
        );

        estado.enviando = false;

        if (resultado.ok) {
            estado.comanda = resultado.dados.comanda;
            estado.rascunho = [];
            estado.referenciaEnvio = null;
            API.rascunho.limpar(chaveDoRascunho());
            API.mostrarAviso(
                el.mensagem,
                'ok',
                resultado.dados.duplicado
                    ? 'Este envio já havia sido gravado. Nada foi duplicado.'
                    : 'Pedido enviado. ' + resultado.dados.itens_gravados + ' item(ns) gravado(s). ' +
                      'Total da comanda: ' + estado.comanda.total_formatado + '.'
            );
            desenharTudo();
            atualizarMesas();
            return;
        }

        if (!resultado.houveResposta) {
            // Não sabemos se gravou: o rascunho e a referência ficam intactos.
            mostrarFalhaDeRede();
        } else {
            const detalhes = (resultado.detalhes && resultado.detalhes.itens) || [];
            API.mostrarAviso(el.mensagem, 'erro', resultado.mensagem, detalhes);
        }
        desenharTudo();
    }

    function mostrarFalhaDeRede() {
        el.mensagem.replaceChildren();
        const caixa = API.criar('div', {classe: 'aviso aviso--atencao'});
        caixa.appendChild(
            API.criar('div', {
                texto:
                    'A conexão falhou e não é possível saber se o pedido foi gravado. ' +
                    'Consulte o estado da comanda antes de tentar de novo.',
            })
        );

        const consultar = API.criar('button', {
            classe: 'botao botao--pequeno',
            texto: 'Consultar comanda no servidor',
            atributos: {type: 'button'},
        });
        consultar.addEventListener('click', consultarComanda);

        const tentar = API.criar('button', {
            classe: 'botao botao--pequeno botao--primario',
            texto: 'Tentar enviar novamente',
            atributos: {type: 'button'},
        });
        tentar.addEventListener('click', enviarPedido);

        caixa.appendChild(
            API.criar('div', {
                classe: 'linha-de-campos',
                atributos: {style: 'margin-top:8px;'},
                filhos: [consultar, tentar],
            })
        );
        el.mensagem.appendChild(caixa);
    }

    async function consultarComanda() {
        if (!estado.comanda) return;
        const resultado = await API.requisitar('/atendimento/api/comandas/' + estado.comanda.id + '/');
        if (!resultado.ok) {
            API.mostrarAviso(el.mensagem, 'erro', resultado.mensagem);
            return;
        }
        estado.comanda = resultado.dados.comanda;
        API.mostrarAviso(
            el.mensagem,
            'info',
            'Estado atual da comanda no servidor: ' + estado.comanda.itens.length +
            ' item(ns), total ' + estado.comanda.total_formatado + '. ' +
            'Se o seu último envio já aparece acima, remova o rascunho em vez de reenviar.'
        );
        desenharTudo();
    }

    /* --- ligações ---------------------------------------------------------- */
    if (el.gradeMesas) {
        el.gradeMesas.addEventListener('click', function (evento) {
            const botao = evento.target.closest('.mesa');
            if (botao) abrirMesa(Number(botao.dataset.mesa));
        });
    }

    el.botaoTrocarMesa.addEventListener('click', voltarParaMesas);
    el.botaoEnviar.addEventListener('click', enviarPedido);
    el.botaoAdicionar.addEventListener('click', adicionarAoRascunho);
    el.botaoCancelarItem.addEventListener('click', function () { el.dialogo.close(); });
    el.busca.addEventListener('input', desenharProdutos);
    el.observacao.addEventListener('input', atualizarContadorObservacao);
    el.quantidade.addEventListener('input', atualizarSubtotalDoItem);
    el.botaoMais.addEventListener('click', function () {
        el.quantidade.value = Math.min(quantidadeValida() + 1, QUANTIDADE_MAXIMA);
        atualizarSubtotalDoItem();
    });
    el.botaoMenos.addEventListener('click', function () {
        el.quantidade.value = Math.max(quantidadeValida() - 1, 1);
        atualizarSubtotalDoItem();
    });

    atualizarMesas();
    window.setInterval(function () {
        if (!estado.mesa) atualizarMesas();
    }, 20000);
})();
