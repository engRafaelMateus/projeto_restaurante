document.addEventListener("DOMContentLoaded", function() {

    /** =========================
     * Input spinners (aumentar/diminuir)
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
    initInputSpinnersDelegation();

    /** =========================
     * Abrir modal ao clicar no produto
     * ========================= */
    const items = document.querySelectorAll(".team-item");

    items.forEach(item => {
        item.addEventListener("click", function() {
            const nome = this.dataset.nome;
            const descricao = this.dataset.descricao;
            const valor = parseFloat(this.dataset.valor);
            const imagem = this.dataset.imagem;

            // Metades
            const outrasMetades = this.dataset.batatas
                ? this.dataset.batatas.split("||").filter(x => x.trim() !== "")
                : [];

            // Preenche modal
            document.getElementById("modalTitulo").textContent = nome;
            document.getElementById("modalDescricao").textContent = descricao;
            document.getElementById("modalValor").textContent = valor.toFixed(2);
            document.getElementById("modalImagem").src = imagem;

            /** Metades */
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

            /** Observação */
            const textarea = document.getElementById('pedidoObservacao');
            const contador = document.getElementById('pedidoObservacaoContador');
            if(textarea && contador){
                textarea.value = "";
                contador.textContent = "140 caracteres restantes";
                textarea.oninput = () => {
                    contador.textContent = `${140 - textarea.value.length} caracteres restantes`;
                };
            }

            /** Abre modal */
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

            const valorOriginal = parseFloat(document.getElementById("modalValor").textContent);
            let valorFinal = valorOriginal;

            // Metade selecionada
            let nomePedido = document.getElementById("modalTitulo").textContent;
            const metadeSelecionada = document.querySelector("input[name='metade']:checked");
            let valorBase = valorOriginal; // **valor da pizza base**
            if(metadeSelecionada){
                const nomeMetade = metadeSelecionada.value;
                const valorMetade = parseFloat(document.querySelector(`#modalMetade input[value="${nomeMetade}"]`).nextElementSibling.querySelector(".valor").textContent.replace("R$","").trim());
                valorBase = (valorOriginal + valorMetade) / 2;
                nomePedido = `Meia ${nomePedido} / Meia ${nomeMetade}`;
            }

            // Categorias
            const categorias = {
                borda: [],
                refrigerante: [],
                sobremesa: [],
                extras: []
            };

            // Borda Recheada (radio)
            const bordaSelecionada = document.querySelector("input[name='borda']:checked");
            if(bordaSelecionada){
                const label = document.querySelector(`label[for="${bordaSelecionada.id}"]`);
                let valorBorda = 0;
                if(label){
                    const valorText = label.textContent.split("- R$")[1];
                    valorBorda = parseFloat(valorText.trim());
                }
                categorias.borda.push(`${bordaSelecionada.value} ${valorBorda.toFixed(2)}`);
                valorFinal += valorBorda;
            }

            // Outras categorias (quantidade)
            const categoriasMap = {
                "modalBebidas": "refrigerante",
                "modalCerveja": "refrigerante",
                "modalSobremesa": "sobremesa",
                "modalExtras": "extras"
            };

            Object.keys(categoriasMap).forEach(id => {
                const cat = categoriasMap[id];
                const container = document.getElementById(id);
                if(container){
                    container.querySelectorAll(".extra-item").forEach(div => {
                        const quantidade = parseInt(div.querySelector(".extra-quantity").value) || 0;
                        if(quantidade > 0){
                            const nomeItem = div.querySelector(".extra-nome-valor span").textContent;
                            const valorItem = parseFloat(div.querySelector(".extra-nome-valor small").textContent.replace("R$","").trim());
                            for(let i=0;i<quantidade;i++){
                                categorias[cat].push(`${nomeItem} ${valorItem.toFixed(2)}`);
                                valorFinal += valorItem;
                            }
                        }
                    });
                }
            });

            // Observação
            const observacao = document.querySelector("#modalProduto #pedidoObservacao").value || "";

            const itemPedido = {
                nome: nomePedido + ` - R$ ${valorBase.toFixed(2)}`, // **valor da pizza base apenas**
                valor: valorFinal,
                categorias,
                observacao,
                quantidade: 1
            };

            let sacola = JSON.parse(localStorage.getItem("sacola")) || [];
            sacola.push(itemPedido);
            localStorage.setItem("sacola", JSON.stringify(sacola));

            // Atualiza contador da sacola
            const contador = document.getElementById("contadorSacola");
            if(contador) contador.textContent = sacola.length;

            if(modalInstance) modalInstance.hide();

            // Atualiza checkout
            atualizarLista();
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

            let detalhes = "";
            for(const cat in item.categorias){
                if(item.categorias[cat].length > 0){
                    const nomeCat = cat.charAt(0).toUpperCase() + cat.slice(1);
                    detalhes += `<strong>${nomeCat}:</strong><br>`;
                    detalhes += item.categorias[cat].map(x => `${x}<br>`).join("");
                    detalhes += "<br>";
                }
            }

            const div = document.createElement("div");
            div.className = "p-2 border mb-2 rounded";
            div.innerHTML = `
                <strong>${item.nome}</strong><br>
                ${detalhes || "Extras: Nenhum"}<br>
                <span><strong>Observação:</strong> ${item.observacao || "-"}</span><br>
                <button class="btn btn-sm btn-danger mt-2 btn-excluir-item" data-index="${i}">Excluir Item</button>
            `;

            listaPedidos.appendChild(div);
        });

        const divTotal = document.createElement("div");
        divTotal.className = "p-2 border mb-2 rounded bg-light text-right";
        divTotal.innerHTML = `<strong>Total da sacola: R$ ${totalSacola.toFixed(2)}</strong>`;
        listaPedidos.appendChild(divTotal);

        // Botão excluir item
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
                mensagem += `${i+1}. ${item.nome}\n`;
                for(const cat in item.categorias){
                    if(item.categorias[cat].length > 0){
                        const nomeCat = cat.charAt(0).toUpperCase() + cat.slice(1);
                        mensagem += `   ${nomeCat}:\n`;
                        item.categorias[cat].forEach(x => {
                            mensagem += `      ${x}\n`;
                        });
                    }
                }
                mensagem += `   Observação: ${item.observacao || "-"}\n\n`;
            });
            mensagem += `Nome: ${nome}\nTelefone: ${telefone}\nPagamento: ${pagamento}\nEndereço: ${endereco}\nObservação: ${observacao}`;

            const url = `https://wa.me/5518991266455?text=${encodeURIComponent(mensagem)}`;
            window.open(url,"_blank");
        });
    }

});
