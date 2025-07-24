# views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db import connection
from django.contrib import messages
from .models import Exercicio, CustomUser, Empresa, ExercicioEmpresa
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse
import pandas as pd
import io

def login_view(request):
    if request.user.is_authenticated:
        return redirect('exercicios')

    error = ''
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        remember_me = request.POST.get('remember_me')

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            if remember_me:
                request.session.set_expiry(60 * 60 * 24 * 30)  # 30 dias
            else:
                request.session.set_expiry(60 * 60 * 24 * 7)   # 7 dias
            return redirect('exercicios')
        else:
            error = 'Usuário ou senha inválidos.'
    return render(request, 'login.html', {'error': error})

@login_required
def lista_exercicios(request):
    if request.method == "POST":
        novo_ano = int(request.POST.get('novo_ano'))
        if not Exercicio.objects.filter(ano=novo_ano).exists():
            schema_name = f"audit_{novo_ano}"
            with connection.cursor() as cursor:
                cursor.execute(f"CREATE SCHEMA IF NOT EXISTS `{schema_name}` DEFAULT CHARACTER SET utf8mb4;")
            Exercicio.objects.create(ano=novo_ano)
            messages.success(request, f'Exercício {novo_ano} criado com sucesso!')
            return redirect('exercicios')
        else:
            messages.warning(request, f'Exercício {novo_ano} já existe!')
            return redirect('exercicios')

    exercicios = Exercicio.objects.all().order_by('-ano')
    return render(request, 'exercicios.html', {'exercicios': exercicios})

@login_required
def atividades_view(request, ano):
    try:
        exercicio = Exercicio.objects.get(ano=ano)
    except Exercicio.DoesNotExist:
        messages.error(request, "Exercício não encontrado!")
        return redirect('exercicios')

    # POST: Excluir empresa deste exercício
    if request.method == "POST" and request.POST.get("excluir_empresa_id"):
        empresa_id = int(request.POST.get("excluir_empresa_id"))
        ExercicioEmpresa.objects.filter(exercicio=exercicio, empresa_id=empresa_id).delete()
        messages.success(request, "Empresa removida deste exercício!")
        return redirect('atividades', ano=ano)

    # POST: Importar empresas para exercício
    if request.method == "POST" and request.POST.getlist('empresas_selecionadas'):
        selecionadas = set(map(int, request.POST.getlist('empresas_selecionadas')))
        empresas_exercicio_ids = set(ExercicioEmpresa.objects.filter(exercicio=exercicio).values_list("empresa_id", flat=True))
        novas = selecionadas - empresas_exercicio_ids
        for empresa_id in novas:
            ExercicioEmpresa.objects.create(exercicio=exercicio, empresa_id=empresa_id)
        messages.success(request, 'Empresas importadas com sucesso!')
        return redirect('atividades', ano=ano)

    # Lista empresas já importadas para este exercício
    empresas_relacionadas = ExercicioEmpresa.objects.filter(exercicio=exercicio).select_related('empresa')
    empresas_exercicio = [ee.empresa for ee in empresas_relacionadas]
    todas_empresas = Empresa.objects.all().order_by('sigla', 'nome_fantasia', 'razao_social')

    # IDs das empresas já vinculadas ao exercício (para checkbox e bloqueio no modal)
    empresas_exercicio_ids = [empresa.id for empresa in empresas_exercicio]

    return render(request, 'atividades.html', {
        'ano': ano,
        'empresas': empresas_exercicio,
        'todas_empresas': todas_empresas,
        'empresas_exercicio_ids': empresas_exercicio_ids,
    })


def home_redirect(request):
    return redirect('login')

@login_required
def configuracoes_view(request):
    return render(request, 'configuracoes.html')

@staff_member_required
def gestor_exercicio_view(request):
    if request.method == "POST" and 'deletar' in request.POST:
        exc_id = int(request.POST.get('deletar'))
        try:
            exc = Exercicio.objects.get(id=exc_id)
            schema_name = f"audit_{exc.ano}"
            with connection.cursor() as cursor:
                cursor.execute(f"DROP DATABASE IF EXISTS `{schema_name}`;")
            exc.delete()
            messages.success(request, f'Exercício {exc.ano} deletado e schema {schema_name} removido com sucesso!')
        except Exercicio.DoesNotExist:
            messages.error(request, 'Exercício não encontrado.')
        return redirect('gestor_exercicio')

    if request.method == "POST" and 'editar' in request.POST:
        exc_id = int(request.POST.get('editar'))
        novo_ano = int(request.POST.get('novo_ano'))
        try:
            exc = Exercicio.objects.get(id=exc_id)
            antigo_ano = exc.ano
            if Exercicio.objects.filter(ano=novo_ano).exclude(id=exc_id).exists():
                messages.error(request, f'O exercício {novo_ano} já existe!')
            else:
                schema_antigo = f"audit_{antigo_ano}"
                schema_novo = f"audit_{novo_ano}"
                with connection.cursor() as cursor:
                    cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{schema_novo}` DEFAULT CHARACTER SET utf8mb4;")
                    cursor.execute(f"SELECT table_name FROM information_schema.tables WHERE table_schema = '{schema_antigo}'")
                    tabelas = [row[0] for row in cursor.fetchall()]
                    for tabela in tabelas:
                        cursor.execute(f"CREATE TABLE `{schema_novo}`.`{tabela}` LIKE `{schema_antigo}`.`{tabela}`;")
                        cursor.execute(f"INSERT INTO `{schema_novo}`.`{tabela}` SELECT * FROM `{schema_antigo}`.`{tabela}`;")
                    cursor.execute(f"DROP DATABASE `{schema_antigo}`;")
                exc.ano = novo_ano
                exc.save()
                messages.success(request, f'Exercício {antigo_ano} alterado para {novo_ano} e schema renomeado!')
        except Exercicio.DoesNotExist:
            messages.error(request, 'Exercício não encontrado.')
        except Exception as e:
            messages.error(request, f'Erro ao renomear schema: {e}')
        return redirect('gestor_exercicio')

    exercicios = Exercicio.objects.all().order_by('-ano')
    return render(request, 'gestor_exercicio.html', {'exercicios': exercicios})

@staff_member_required
def gestor_usuario_view(request):
    editar_user = None
    usuarios = CustomUser.objects.all().order_by('nome')

    # Cadastro
    if request.method == 'POST' and 'criar_usuario' in request.POST:
        nome = request.POST.get('nome', '').strip()
        cargo = request.POST.get('cargo', '').strip()
        username = request.POST.get('username', '').strip()
        sigla = request.POST.get('sigla', '').strip().upper()
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')
        is_active = bool(request.POST.get('is_active'))

        if CustomUser.objects.filter(sigla=sigla).exists():
            messages.error(request, 'Já existe um usuário com essa sigla!')
        elif password1 != password2:
            messages.error(request, 'Senhas não conferem!')
        elif not all([nome, username, sigla, password1]):
            messages.error(request, 'Preencha todos os campos obrigatórios!')
        else:
            user = CustomUser.objects.create_user(
                username=username,
                nome=nome,
                cargo=cargo,
                sigla=sigla,
                password=password1,
                is_active=is_active
            )
            messages.success(request, 'Usuário cadastrado com sucesso!')
            return redirect('gestor_usuario')

    # Editar (mostrar formulário de edição preenchido)
    if request.method == 'POST' and 'editar_usuario' in request.POST and not request.POST.get('nome'):
        user_id = int(request.POST.get('editar_usuario'))
        editar_user = get_object_or_404(CustomUser, pk=user_id)
        return render(request, 'gestor_usuario.html', {
            'usuarios': usuarios,
            'editar_user': editar_user
        })

    # Edição (salvar)
    if request.method == 'POST' and 'editar_usuario' in request.POST and request.POST.get('nome'):
        user_id = int(request.POST.get('editar_usuario'))
        user = get_object_or_404(CustomUser, pk=user_id)
        nome = request.POST.get('nome', '').strip()
        cargo = request.POST.get('cargo', '').strip()
        username = request.POST.get('username', '').strip()
        sigla = request.POST.get('sigla', '').strip().upper()
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')
        is_active = bool(request.POST.get('is_active'))

        if CustomUser.objects.filter(sigla=sigla).exclude(id=user_id).exists():
            messages.error(request, 'Já existe outro usuário com essa sigla!')
            editar_user = user
        elif password1 and password1 != password2:
            messages.error(request, 'Senhas não conferem!')
            editar_user = user
        else:
            user.nome = nome
            user.cargo = cargo
            user.username = username
            user.sigla = sigla
            user.is_active = is_active
            if password1:
                user.set_password(password1)
            user.save()
            messages.success(request, 'Usuário atualizado com sucesso!')
            return redirect('gestor_usuario')

        return render(request, 'gestor_usuario.html', {
            'usuarios': usuarios,
            'editar_user': editar_user
        })

    # Ativar/Inativar
    if request.method == 'POST' and 'toggle_status' in request.POST:
        user_id = int(request.POST.get('toggle_status'))
        user = CustomUser.objects.get(id=user_id)
        user.is_active = not user.is_active
        user.save()
        messages.success(request, f'Usuário {"ativado" if user.is_active else "inativado"} com sucesso!')
        return redirect('gestor_usuario')

    # Deletar
    if request.method == 'POST' and 'deletar_usuario' in request.POST:
        user_id = int(request.POST.get('deletar_usuario'))
        CustomUser.objects.filter(id=user_id).delete()
        messages.success(request, 'Usuário deletado com sucesso!')
        return redirect('gestor_usuario')

    # Alterar senha individual
    if request.method == 'POST' and 'alterar_senha' in request.POST:
        user_id = int(request.POST.get('alterar_senha'))
        nova_senha = request.POST.get('nova_senha')
        user = CustomUser.objects.get(id=user_id)
        user.set_password(nova_senha)
        user.save()
        if user_id == request.user.id:
            logout(request)
            return redirect('login')
        else:
            messages.success(request, 'Senha alterada com sucesso!')
            return redirect('gestor_usuario')

    return render(request, 'gestor_usuario.html', {
        'usuarios': usuarios,
        'editar_user': editar_user
    })

@login_required
def alterar_senha(request):
    if request.method == 'POST':
        nova_senha = request.POST.get('nova_senha')
        if nova_senha:
            user = request.user
            user.set_password(nova_senha)
            user.save()
            logout(request)
            messages.success(request, 'Senha alterada com sucesso! Faça login novamente.')
            return redirect('login')
        else:
            messages.error(request, 'Digite uma nova senha.')
    return render(request, 'alterar_senha.html')

@login_required
def gestor_empresas_view(request):
    empresas = Empresa.objects.all().order_by('razao_social')
    editar_empresa = None

    # IMPORTAÇÃO EM MASSA DE EMPRESAS
    if request.method == "POST" and 'importar_excel_empresas' in request.POST and request.FILES.get('excel_empresas'):
        excel_file = request.FILES["excel_empresas"]
        try:
            df = pd.read_excel(excel_file)
            required_cols = ['Razão Social', 'Nome Fantasia', 'Sigla', 'CNPJ', 'Tipo de Empresa', 'Interesse Público']
            if not all(col in df.columns for col in required_cols):
                messages.error(request, "Colunas inválidas. O padrão é: Razão Social, Nome Fantasia, Sigla, CNPJ, Tipo de Empresa, Interesse Público.")
            else:
                count = 0
                for idx, row in df.iterrows():
                    razao_social = str(row['Razão Social']).strip()
                    nome_fantasia = str(row['Nome Fantasia']).strip()
                    sigla = str(row['Sigla']).strip()
                    cnpj = str(row['CNPJ']).strip()
                    tipo_empresa = str(row['Tipo de Empresa']).strip()
                    interesse_publico = str(row['Interesse Público']).strip()
                    if not all([razao_social, cnpj, tipo_empresa, interesse_publico]):
                        continue
                    if not Empresa.objects.filter(cnpj=cnpj).exists():
                        Empresa.objects.create(
                            razao_social=razao_social,
                            nome_fantasia=nome_fantasia,
                            sigla=sigla,
                            cnpj=cnpj,
                            tipo_empresa=tipo_empresa,
                            interesse_publico=interesse_publico
                        )
                        count += 1
                messages.success(request, f'{count} novas empresas importadas com sucesso!')
        except Exception as e:
            messages.error(request, f"Erro ao importar: {e}")
        return redirect('gestor_empresas')

    # Cadastro manual
    if request.method == "POST" and 'cadastrar_empresa' in request.POST:
        razao_social = request.POST.get('razao_social', '').strip()
        nome_fantasia = request.POST.get('nome_fantasia', '').strip()
        sigla = request.POST.get('sigla', '').strip()
        cnpj = request.POST.get('cnpj', '').strip()
        tipo_empresa = request.POST.get('tipo_empresa', '')
        interesse_publico = request.POST.get('interesse_publico', '')

        if razao_social and cnpj and tipo_empresa and interesse_publico:
            if not Empresa.objects.filter(cnpj=cnpj).exists():
                Empresa.objects.create(
                    razao_social=razao_social,
                    nome_fantasia=nome_fantasia,
                    sigla=sigla,
                    cnpj=cnpj,
                    tipo_empresa=tipo_empresa,
                    interesse_publico=interesse_publico
                )
                messages.success(request, "Empresa cadastrada com sucesso!")
            else:
                messages.error(request, "Já existe uma empresa com esse CNPJ!")
        else:
            messages.error(request, "Preencha todos os campos obrigatórios.")
        return redirect('gestor_empresas')

    # Editar (abrir formulário preenchido)
    if request.method == "POST" and 'editar_empresa' in request.POST and not request.POST.get('razao_social'):
        empresa_id = int(request.POST.get('editar_empresa'))
        editar_empresa = Empresa.objects.get(id=empresa_id)
        return render(request, 'gestor_empresas.html', {
            'empresas': empresas,
            'editar_empresa': editar_empresa
        })

    # Salvar edição
    if request.method == "POST" and 'editar_empresa' in request.POST and request.POST.get('razao_social'):
        empresa_id = int(request.POST.get('editar_empresa'))
        empresa = Empresa.objects.get(id=empresa_id)
        empresa.razao_social = request.POST.get('razao_social', '').strip()
        empresa.nome_fantasia = request.POST.get('nome_fantasia', '').strip()
        empresa.sigla = request.POST.get('sigla', '').strip()
        empresa.cnpj = request.POST.get('cnpj', '').strip()
        empresa.tipo_empresa = request.POST.get('tipo_empresa', '')
        empresa.interesse_publico = request.POST.get('interesse_publico', '')
        empresa.save()
        messages.success(request, "Empresa atualizada com sucesso!")
        return redirect('gestor_empresas')

    # Deletar
    if request.method == "POST" and 'deletar_empresa' in request.POST:
        empresa_id = int(request.POST.get('deletar_empresa'))
        Empresa.objects.filter(id=empresa_id).delete()
        messages.success(request, "Empresa deletada com sucesso!")
        return redirect('gestor_empresas')

    return render(request, 'gestor_empresas.html', {
        'empresas': empresas,
        'editar_empresa': editar_empresa
    })

# ----------- DOWNLOAD MODELO EXCEL EMPRESAS -----------
@login_required
def download_excel_empresas(request):
    df = pd.DataFrame([{
        "Razão Social": "Empresa Exemplo Ltda",
        "Nome Fantasia": "Empresa Exemplo",
        "Sigla": "EXEMPLO",
        "CNPJ": "00.000.000/0001-00",
        "Tipo de Empresa": "Empresas Com Fins Lucrativos",
        "Interesse Público": "Sim"
    }])
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False)
    buffer.seek(0)
    response = HttpResponse(
        buffer,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="modelo_empresas.xlsx"'
    return response

@login_required
def gestao_atividades_empresa_view(request, ano, empresa_id):
    empresa = get_object_or_404(Empresa, id=empresa_id)
    return render(request, 'gestao_atividades_empresa.html', {
        'empresa': empresa,
        'ano': ano,
    })
