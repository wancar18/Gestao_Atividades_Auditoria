# models.py

from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager

class CustomUserManager(BaseUserManager):
    def create_user(self, username, password=None, nome='', cargo='', sigla=None, **extra_fields):
        if not username:
            raise ValueError('O usuário deve ter um nome de usuário')
        user = self.model(username=username, nome=nome, cargo=cargo, sigla=sigla, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password, nome='', cargo='', sigla=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(username, password, nome, cargo, sigla, **extra_fields)

class CustomUser(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(max_length=150, unique=True)
    nome = models.CharField(max_length=100, blank=True)
    cargo = models.CharField(max_length=100, blank=True)
    sigla = models.CharField("Sigla", max_length=20, unique=True, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    objects = CustomUserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['sigla']

    def save(self, *args, **kwargs):
        if self.sigla:
            self.sigla = self.sigla.upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.username

class Exercicio(models.Model):
    ano = models.IntegerField(unique=True)
    def __str__(self):
        return str(self.ano)

# === NOVOS MODELOS DE ATIVIDADES ===

class CategoriaAtividade(models.Model):
    nome = models.CharField(max_length=150, unique=True)
    def __str__(self):
        return self.nome

class SubitemAtividade(models.Model):
    categoria = models.ForeignKey(CategoriaAtividade, on_delete=models.CASCADE, related_name='subitens')
    nome = models.CharField(max_length=150)
    class Meta:
        unique_together = ('categoria', 'nome')
    def __str__(self):
        return f'{self.categoria.nome} > {self.nome}'

class Atividade(models.Model):
    subitem = models.ForeignKey(SubitemAtividade, on_delete=models.CASCADE, related_name='atividades')
    nome = models.CharField(max_length=200)
    tempo_estimado = models.CharField(max_length=50, blank=True, help_text="Exemplo: 1 dia, 2 horas")
    class Meta:
        unique_together = ('subitem', 'nome', 'tempo_estimado')
    def __str__(self):
        return f'{self.subitem} > {self.nome} ({self.tempo_estimado})'

class Empresa(models.Model):
    TIPO_EMPRESA_CHOICES = [
        ("Terceiro Setor Sem Fins Lucrativos", "Terceiro Setor Sem Fins Lucrativos"),
        ("Empresas Com Fins Lucrativos", "Empresas Com Fins Lucrativos"),
        ("Clube de Futebol", "Clube de Futebol"),
        ("Estatais", "Estatais"),
        ("Estatais em Liquidação", "Estatais em Liquidação"),
        ("Condominio", "Condomínio"),
    ]
    INTERESSE_PUBLICO_CHOICES = [
        ("Sim", "Sim"),
        ("Não", "Não"),
    ]

    razao_social = models.CharField(max_length=255)
    nome_fantasia = models.CharField(max_length=255, blank=True)
    sigla = models.CharField("Sigla Resumida", max_length=20, blank=True)
    cnpj = models.CharField(max_length=18, unique=True)  # pode usar django-localflavor para validar melhor
    tipo_empresa = models.CharField(max_length=50, choices=TIPO_EMPRESA_CHOICES)
    interesse_publico = models.CharField(max_length=3, choices=INTERESSE_PUBLICO_CHOICES)

    def __str__(self):
        return f"{self.razao_social} ({self.sigla})"

# NOVO MODELO: Empresas importadas para cada exercício
class ExercicioEmpresa(models.Model):
    exercicio = models.ForeignKey(Exercicio, on_delete=models.CASCADE, related_name='empresas_exercicio')
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='exercicios_empresa')
    importada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('exercicio', 'empresa')
        verbose_name = "Empresa Importada no Exercício"
        verbose_name_plural = "Empresas Importadas nos Exercícios"

    def __str__(self):
        return f"{self.empresa.sigla or self.empresa.razao_social} - {self.exercicio.ano}"

# NOVO MODELO - Atividades importadas para Empresa (por exercício)
class AtividadeEmpresa(models.Model):
    PERIODO_CHOICES = [
        ("1º Trimestre", "1º Trimestre"),
        ("2º Trimestre", "2º Trimestre"),
        ("3º Trimestre", "3º Trimestre"),
        ("4º Trimestre", "4º Trimestre"),
    ]
    STATUS_CHOICES = [
        ("Não Iniciado", "Não Iniciado"),
        ("Em Execução", "Em Execução"),
        ("Concluso", "Concluso"),
        ("N/A", "N/A"),
    ]

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='atividades_empresas')
    exercicio = models.ForeignKey(Exercicio, on_delete=models.CASCADE, related_name='atividades_empresas')
    categoria = models.ForeignKey(CategoriaAtividade, on_delete=models.PROTECT)
    subitem = models.ForeignKey(SubitemAtividade, on_delete=models.PROTECT)
    atividade = models.ForeignKey(Atividade, on_delete=models.PROTECT)
    periodo = models.CharField(max_length=20, choices=PERIODO_CHOICES, blank=True)
    data_inicio = models.DateField(blank=True, null=True)
    data_fim = models.DateField(blank=True, null=True)
    prazo = models.CharField(max_length=30, blank=True)  # pode armazenar o tempo_estimado, se quiser
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Não Iniciado")
    usuario = models.ForeignKey(
        CustomUser,
        to_field="sigla",
        db_column="usuario_sigla",
        on_delete=models.PROTECT,
        verbose_name="Responsável (Sigla do Usuário)"
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.empresa.sigla} - {self.categoria.nome} - {self.atividade.nome} ({self.status})"


class EmpresaExercicio(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    exercicio = models.ForeignKey(Exercicio, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('empresa', 'exercicio')

    def __str__(self):
        return f"{self.empresa.sigla or self.empresa.razao_social} - {self.exercicio.ano}"
