document.addEventListener("DOMContentLoaded", function() {

    /** =========================
     * Input Spinner via delegação
     * ========================= */
    function initInputSpinnersDelegation() {
        const modal = document.getElementById("modalProduto");
        if(!modal) return;

        modal.addEventListener("click", function(e) {
            const target = e.target;

            if(target.classList.contains("btn-increase")) {
                const input = modal.querySelector(`.extra-quantity[data-id="${target.dataset.id}"]`);
                if(input) input.value = parseInt(input.value || 0) + 1;
            }

            if(target.classList.contains("btn-decrease")) {
                const input = modal.querySelector(`.extra-quantity[data-id="${target.dataset.id}"]`);
                if(input){
                    let val = parseInt(input.value || 0);
                    if(val > 0) input.value = val - 1;
                }
            }
        });
    }

    // Inicializa a delegação uma vez
    initInputSpinnersDelegation();

    /** =========================
     * Modal e seleção de produto
     * ========================= */
    const items = document.querySelectorAll(".team-item");

    items.forEach(item => {
        item.addEventListener("click", function() {
            const nome = this.dataset.nome;
            const descricao = this.dataset.descricao;
            const valor = parseFloat(this.dataset.valor);
            const imagem = this.dataset.imagem;

            // Extras e Metades
            const outrasMetades = this.dataset.batatas
                ? this.dataset.batatas.split("||").filter(x => x.trim() !== "")
                : [];
            const extrasRaw = this.dataset.extras
                ? this.dataset.extras.split("||").filter(x => x.trim() !== "")
                : [];

            // Preenche dados do modal
            document.getElementById("modalTitulo").textContent = nome;
            document.getElementById("modalDescricao").textContent = descricao;
            document.getElementById("modalValor").textContent = valor.toFixed(2);
            document.getElementById("modalImagem").src = imagem;

            /** =========================
             * Metades (opcional)
             * ========================= */
            const metadeContainer = document.getElementById("modalMetade");
            metadeContainer.innerHTML = "";

            outrasMetades.forEach((item, i) => {
                const parts = item.trim().split("|");
                const pizzaNome = parts[0] || "";
                const pizzaValor = parseFloat(parts[1] || "0.00");
                const pizzaImg = parts[2] || "";

                const id = `metade-${i}`;
                const div = document.createElement("div");
                div.classList.add("d-flex", "align-items-center", "mb-2");
                div.innerHTML = `
                    <input type="radio" name="metade" id="${id}" value="${pizzaNome}" class="d-none">
                    <label for="${id}" class="d-flex align-items-center justify-content-between w-100 p-2 border rounded" style="cursor:pointer;">
                        <span class="nome">${pizzaNome}</span>
                        <span class="valor">R$ ${pizzaValor.toFixed(2)}</span>
                        <img src="${pizzaImg}" alt="${pizzaNome}" style="width:70px; height:70px; object-fit:cover; margin-left:10px; border-radius:6px;">
                    </label>
                `;

                const radio = div.querySelector("input");
                const label = div.querySelector("label");

                label.addEventListener("click", function(e) {
                    if (radio.checked) {
                        radio.checked = false;
                        label.classList.remove("selected");
                        e.preventDefault();
                    } else {
                        document.querySelectorAll("#modalMetade label").forEach(l => l.classList.remove("selected"));
                        radio.checked = true;
                        label.classList.add("selected");
                    }
                });

                metadeContainer.appendChild(div);
            });

            /** =========================
             * Extras
             * ========================= */
            const extrasContainer = document.getElementById("modalExtras");
            extrasContainer.innerHTML = "";

            extrasRaw.forEach((extraStr, i) => {
                const id = `extra-${i}`;
                const partes = extraStr.trim().split(" ");
                const valorExtra = partes.pop(); // último elemento é o valor
                const nomeExtra = partes.join(" "); // resto é o nome

                const div = document.createElement("div");
                div.classList.add("extra-item");

                div.innerHTML = `
                    <div class="extra-nome-valor">
                        <span>${nomeExtra}</span>
                        <small>R$ ${valorExtra}</small>
                    </div>
                    <div class="extra-controls">
                        <button type="button" class="btn btn-decrease" data-id="${id}">-</button>
                        <input type="text" class="extra-quantity" value="0" readonly data-id="${id}">
                        <button type="button" class="btn btn-increase" data-id="${id}">+</button>
                    </div>
                `;

                extrasContainer.appendChild(div);
            });

            /** =========================
             * Observação
             * ========================= */
            const textarea = document.getElementById('pedidoObservacao');
            const contador = document.getElementById('pedidoObservacaoContador');
            if(textarea && contador){
                textarea.value = "";
                contador.textContent = "140 caracteres restantes";
                textarea.oninput = () => {
                    contador.textContent = `${140 - textarea.value.length} caracteres restantes`;
                };
            }

            /** =========================
             * Abre modal
             * ========================= */
            const modalEl = document.getElementById("modalProduto");
            if(modalEl){
                const modal = new bootstrap.Modal(modalEl);
                modal.show();
                modalEl.modalInstance = modal;
            }
        });
    });

    /** =========================
     * Adicionar item à sacola
     * ========================= */
    document.addEventListener("click", function(e){
        if(e.target.closest(".btn-adicionar-sacola")){
            const modalEl = document.getElementById("modalProduto");
            const modalInstance = modalEl.modalInstance;

            let nome = document.getElementById("modalTitulo").textContent;
            const valorOriginal = parseFloat(document.getElementById("modalValor").textContent);

            let valorFinal = valorOriginal;

            // Checa se selecionou outra metade
            const metadeSelecionada = document.querySelector("input[name='metade']:checked");
            if(metadeSelecionada){
                const nomeMetade = metadeSelecionada.value;
                const valorMetade = parseFloat(document.querySelector(`#modalMetade input[value="${nomeMetade}"]`).nextElementSibling.querySelector(".valor").textContent.replace("R$","").trim());
                valorFinal = ((valorOriginal + valorMetade) / 2);
                nome = `Meia ${nome} / Meia ${nomeMetade}`;
            }

            // Extras
            const extrasSelecionados = [];
            document.querySelectorAll("#modalExtras .extra-item, #modalBebidas .extra-item, #modalCerveja .extra-item, #modalSobremesa .extra-item").forEach(div => {
                const quantidade = parseInt(div.querySelector(".extra-quantity").value) || 0;
                if(quantidade > 0){
                    const nomeExtra = div.querySelector(".extra-nome-valor span").textContent;
                    const valorExtra = parseFloat(div.querySelector(".extra-nome-valor small").textContent.replace("R$","").trim());
                    for(let i=0;i<quantidade;i++){
                        extrasSelecionados.push(`${nomeExtra} ${valorExtra.toFixed(2)}`);
                        valorFinal += valorExtra;
                    }
                }
            });

            // Observação
            const observacao = document.querySelector("#modalProduto #pedidoObservacao").value || "";

            const itemPedido = {
                nome,
                valor: valorFinal,
                extras: extrasSelecionados,
                observacao,
                quantidade: 1
            };

            let sacola = JSON.parse(localStorage.getItem("sacola")) || [];
            sacola.push(itemPedido);
            localStorage.setItem("sacola", JSON.stringify(sacola));

            const contador = document.getElementById("contadorSacola");
            if(contador) contador.textContent = sacola.length;

            if(modalInstance) modalInstance.hide();
        }
    });

    /** =========================
     * Checkout e manipulação do carrinho
     * ========================= */
    const listaPedidos = document.getElementById("listaPedidos");
    const textareaCheckout = document.getElementById('pedidoObservacao');
    const contadorCheckout = document.getElementById('contadorObservacao');
    const btnLimpar = document.getElementById("btnLimparCarrinho");
    const btnEnviar = document.getElementById("btnEnviarWhatsApp");

    function atualizarLista() {
        listaPedidos.innerHTML = "";
        const sacola = JSON.parse(localStorage.getItem("sacola")) || [];

        if(sacola.length === 0){
            listaPedidos.innerHTML = "<p>Seu carrinho está vazio.</p>";
            return;
        }

        let totalSacola = 0;
        sacola.forEach((item, i) => {
            const totalItem = item.valor;
            totalSacola += totalItem;

            const extrasHTML = item.extras.length > 0 ? item.extras.join(", ") : "Nenhum";

            const div = document.createElement("div");
            div.className = "p-2 border mb-2 rounded";
            div.innerHTML = `
                <strong>${item.nome}</strong> - R$ ${totalItem.toFixed(2)}<br>
                <span><strong>Extras:</strong> ${extrasHTML}</span><br>
                <span><strong>Observação:</strong> ${item.observacao || "-"}</span><br>
                <button class="btn btn-sm btn-danger mt-2 btn-excluir-item" data-index="${i}">Excluir Item</button>
            `;
            listaPedidos.appendChild(div);
        });

        const divTotal = document.createElement("div");
        divTotal.className = "p-2 border mb-2 rounded bg-light text-right";
        divTotal.innerHTML = `<strong>Total da sacola: R$ ${totalSacola.toFixed(2)}</strong>`;
        listaPedidos.appendChild(divTotal);

        document.querySelectorAll(".btn-excluir-item").forEach(btn => {
            btn.addEventListener("click", function() {
                const index = parseInt(this.dataset.index);
                let sacolaAtual = JSON.parse(localStorage.getItem("sacola")) || [];
                sacolaAtual.splice(index,1);
                localStorage.setItem("sacola", JSON.stringify(sacolaAtual));
                atualizarLista();
            });
        });
    }

    if(listaPedidos) atualizarLista();

    if(textareaCheckout && contadorCheckout){
        textareaCheckout.addEventListener("input", () => {
            contadorCheckout.textContent = `${140 - textareaCheckout.value.length} caracteres restantes`;
        });
    }

    if(btnLimpar){
        btnLimpar.addEventListener("click", function(){
            if(confirm("Tem certeza que deseja limpar todo o carrinho?")){
                localStorage.removeItem("sacola");
                alert("Carrinho limpo!");
                atualizarLista();
            }
        });
    }

    if(btnEnviar){
        btnEnviar.addEventListener("click", function(){
            const nome = document.getElementById("clienteNome").value;
            const telefone = document.getElementById("clienteTelefone").value;
            const endereco = document.getElementById("clienteEndereco").value;
            const pagamento = document.getElementById("clientePagamento").value;
            const observacao = textareaCheckout.value;
            const sacola = JSON.parse(localStorage.getItem("sacola")) || [];

            if(!nome || !telefone || !endereco || !pagamento || sacola.length === 0){
                alert("Preencha todos os campos e adicione pelo menos um pedido.");
                return;
            }

            let mensagem = `Olá! Gostaria de fazer o pedido:\n\n`;
            sacola.forEach((item, i) => {
                mensagem += `${i+1}. ${item.nome} - R$ ${item.valor.toFixed(2)}\n`;
                mensagem += `   Extras: ${item.extras.length > 0 ? item.extras.join(", ") : 'Nenhum'}\n`;
                mensagem += `   Observação: ${item.observacao || "-"}\n\n`;
            });
            mensagem += `Nome: ${nome}\nTelefone: ${telefone}\nPagamento: ${pagamento}\nEndereço: ${endereco}\nObservação: ${observacao}`;

            const url = `https://wa.me/5518991266455?text=${encodeURIComponent(mensagem)}`;
            window.open(url,"_blank");
        });
    }

});
