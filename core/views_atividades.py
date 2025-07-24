from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import CategoriaAtividade, SubitemAtividade, Atividade, Empresa
import pandas as pd
from django.http import HttpResponse, JsonResponse
from django.template.loader import render_to_string

@login_required
def gestor_atividades_view(request):
    # Pré-carregar categorias iniciais se não existirem
    categorias_iniciais = [
        "Auditoria Contábil", "Controles Internos", "Circularizações",
        "Encerramento", "Gestão da Qualidade", "Revisão"
    ]
    for nome in categorias_iniciais:
        CategoriaAtividade.objects.get_or_create(nome=nome)

    # === AÇÕES DE CRUD (POST) ===

    # Adicionar Categoria
    if request.method == "POST" and "adicionar_categoria" in request.POST:
        nome = request.POST.get("categoria_nome")
        if nome and not CategoriaAtividade.objects.filter(nome=nome).exists():
            CategoriaAtividade.objects.create(nome=nome)
            messages.success(request, f'Categoria "{nome}" criada!')
        else:
            messages.error(request, "Categoria já existe ou campo vazio.")
        return redirect('gestor_atividades')

    # Editar Categoria
    if request.method == "POST" and "salvar_categoria" in request.POST:
        cat_id = request.POST.get("edit_categoria_id")
        novo_nome = request.POST.get("edit_categoria_nome")
        if cat_id and novo_nome:
            cat = CategoriaAtividade.objects.get(id=cat_id)
            cat.nome = novo_nome
            cat.save()
            messages.success(request, "Categoria atualizada com sucesso!")
        return redirect('gestor_atividades')

    # Deletar Categoria
    if request.method == "POST" and "deletar_categoria" in request.POST:
        cat_id = request.POST.get("del_categoria_id")
        try:
            CategoriaAtividade.objects.get(id=cat_id).delete()
            messages.success(request, "Categoria deletada!")
        except:
            messages.error(request, "Erro ao deletar categoria.")
        return redirect('gestor_atividades')

    # Adicionar Subitem
    if request.method == "POST" and "adicionar_subitem" in request.POST:
        cat_id = request.POST.get("categoria_id")
        nome = request.POST.get("subitem_nome")
        if cat_id and nome:
            cat = CategoriaAtividade.objects.get(id=cat_id)
            if not SubitemAtividade.objects.filter(categoria=cat, nome=nome).exists():
                SubitemAtividade.objects.create(categoria=cat, nome=nome)
                messages.success(request, f'Subitem "{nome}" criado!')
            else:
                messages.error(request, "Subitem já existe nessa categoria.")
        return redirect('gestor_atividades')

    # Editar Subitem
    if request.method == "POST" and "salvar_subitem" in request.POST:
        sub_id = request.POST.get("edit_subitem_id")
        novo_nome = request.POST.get("edit_subitem_nome")
        if sub_id and novo_nome:
            sub = SubitemAtividade.objects.get(id=sub_id)
            sub.nome = novo_nome
            sub.save()
            messages.success(request, "Subitem atualizado com sucesso!")
        return redirect('gestor_atividades')

    # Deletar Subitem
    if request.method == "POST" and "deletar_subitem" in request.POST:
        sub_id = request.POST.get("del_subitem_id")
        try:
            SubitemAtividade.objects.get(id=sub_id).delete()
            messages.success(request, "Subitem deletado!")
        except:
            messages.error(request, "Erro ao deletar subitem.")
        return redirect('gestor_atividades')

    # Adicionar Atividade
    if request.method == "POST" and "adicionar_atividade" in request.POST:
        subitem_id = request.POST.get("subitem_id")
        nome = request.POST.get("atividade_nome")
        tempo = request.POST.get("tempo_estimado")
        if subitem_id and nome and tempo:
            sub = SubitemAtividade.objects.get(id=subitem_id)
            if not Atividade.objects.filter(subitem=sub, nome=nome, tempo_estimado=tempo).exists():
                Atividade.objects.create(subitem=sub, nome=nome, tempo_estimado=tempo)
                messages.success(request, f'Atividade "{nome}" criada!')
            else:
                messages.error(request, "Atividade já existe nesse subitem.")
        return redirect('gestor_atividades')

    # Editar Atividade
    if request.method == "POST" and "salvar_atividade" in request.POST:
        ati_id = request.POST.get("edit_atividade_id")
        novo_nome = request.POST.get("edit_atividade_nome")
        novo_tempo = request.POST.get("edit_tempo_estimado")
        if ati_id and novo_nome and novo_tempo:
            ati = Atividade.objects.get(id=ati_id)
            ati.nome = novo_nome
            ati.tempo_estimado = novo_tempo
            ati.save()
            messages.success(request, "Atividade atualizada com sucesso!")
        return redirect('gestor_atividades')

    # Deletar Atividade
    if request.method == "POST" and "deletar_atividade" in request.POST:
        ati_id = request.POST.get("del_atividade_id")
        try:
            Atividade.objects.get(id=ati_id).delete()
            messages.success(request, "Atividade deletada!")
        except:
            messages.error(request, "Erro ao deletar atividade.")
        return redirect('gestor_atividades')

    # Importação de atividades por Excel
    if request.method == "POST" and "importar_excel" in request.POST and request.FILES.get("excel_file"):
        excel_file = request.FILES["excel_file"]
        try:
            df = pd.read_excel(excel_file)
            required_cols = ['Categoria', 'Subitem', 'Atividade', 'Tempo estimado (dias)']
            if not all(col in df.columns for col in required_cols):
                messages.error(request, "Colunas inválidas. Padrão: Categoria, Subitem, Atividade, Tempo estimado (dias)")
            else:
                count = 0
                for idx, row in df.iterrows():
                    cat_nome = str(row['Categoria']).strip()
                    sub_nome = str(row['Subitem']).strip()
                    ati_nome = str(row['Atividade']).strip()
                    tempo = str(row['Tempo estimado (dias)']).strip()
                    if not all([cat_nome, sub_nome, ati_nome, tempo]):
                        continue
                    cat, _ = CategoriaAtividade.objects.get_or_create(nome=cat_nome)
                    sub, _ = SubitemAtividade.objects.get_or_create(categoria=cat, nome=sub_nome)
                    if not Atividade.objects.filter(subitem=sub, nome=ati_nome, tempo_estimado=tempo).exists():
                        Atividade.objects.create(subitem=sub, nome=ati_nome, tempo_estimado=tempo)
                        count += 1
                messages.success(request, f'{count} novas atividades importadas com sucesso!')
        except Exception as e:
            messages.error(request, f"Erro ao importar: {e}")
        return redirect('gestor_atividades')

    # ===== FILTROS DINÂMICOS PARA TABELA =====
    filtro_categoria = request.GET.get('categoria')
    filtro_subitem = request.GET.get('subitem')
    search_atividade = (
        request.GET.get('atividade_search', '') or
        request.GET.get('busca', '')
    )


    atividades = Atividade.objects.all().select_related('subitem', 'subitem__categoria')
    if filtro_categoria:
        atividades = atividades.filter(subitem__categoria_id=filtro_categoria)
    if filtro_subitem:
        atividades = atividades.filter(subitem_id=filtro_subitem)
    if search_atividade:
        atividades = atividades.filter(nome__icontains=search_atividade)

    context = {
        'todas_categorias': CategoriaAtividade.objects.all(),
        'todos_subitens': SubitemAtividade.objects.all(),
        'todas_atividades': Atividade.objects.all(),
        'atividades': atividades,  # <-- nome padronizado, igual ao partial
        'request': request,
    }
    return render(request, 'gestor_atividades.html', context)

@login_required
def atividades_partial(request):
    filtro_categoria = request.GET.get('categoria')
    filtro_subitem = request.GET.get('subitem')
    search_atividade = request.GET.get('atividade_search', '')

    atividades = Atividade.objects.all().select_related('subitem', 'subitem__categoria')
    if filtro_categoria:
        atividades = atividades.filter(subitem__categoria_id=filtro_categoria)
    if filtro_subitem:
        atividades = atividades.filter(subitem_id=filtro_subitem)
    if search_atividade:
        atividades = atividades.filter(nome__icontains=search_atividade)

    html = render_to_string('partials/_lista_atividades.html', {
        'atividades': atividades,  # <-- padronizado
        'request': request
    })
    return JsonResponse({'html': html})

@login_required
def download_excel_modelo(request):
    df = pd.DataFrame([
        {
            "Categoria": "Auditoria Contábil",
            "Subitem": "Solicitações",
            "Atividade": "Enviar Solicitação de Documentos",
            "Tempo estimado (dias)": "1"
        }
    ])
    import io
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False)
    buffer.seek(0)
    response = HttpResponse(
        buffer,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="modelo_atividades.xlsx"'
    return response

