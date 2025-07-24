from django.urls import path
from .views import (
    login_view, lista_exercicios, atividades_view, home_redirect,
    configuracoes_view, gestor_exercicio_view, gestor_usuario_view, gestor_empresas_view, gestao_atividades_empresa_view,
    download_excel_empresas,   # <-- DOWNLOAD DE EMPRESAS
)
from .views_atividades import (
    gestor_atividades_view,
    download_excel_modelo,
    atividades_partial,
)

urlpatterns = [
    path('', home_redirect, name='home'),
    path('login/', login_view, name='login'),
    path('exercicios/', lista_exercicios, name='exercicios'),
    path('atividades/<int:ano>/', atividades_view, name='atividades'),
    path('configuracoes/', configuracoes_view, name='configuracoes'),
    path('gestor-exercicio/', gestor_exercicio_view, name='gestor_exercicio'),
    path('gestor-usuario/', gestor_usuario_view, name='gestor_usuario'),
    path('gestor-atividades/', gestor_atividades_view, name='gestor_atividades'),
    path('download-excel-modelo/', download_excel_modelo, name='download_excel_modelo'),
    path('atividades-partial/', atividades_partial, name='atividades_partial'),
    path('gestor-empresas/', gestor_empresas_view, name='gestor_empresas'),
    path('download-excel-empresas/', download_excel_empresas, name='download_excel_empresas'),
    path('atividades/<int:ano>/empresa/<int:empresa_id>/', gestao_atividades_empresa_view, name='gestao_atividades_empresa'),
]
