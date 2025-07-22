import streamlit as st 
import pandas as pd
import plotly.express as px

st.title('Unimed Goiânia: Análise de Dados')

tab1, tab2, tab3 = st.tabs(["Informação Geral", "Dados Sobre Atendimentos", "Taxa de No-Show"])


conn = st.connection("neon", type="sql")

with tab1:
    st.title('TABELA PEP')
    df= conn.query('SELECT * FROM unimed.base_pep;', ttl="10m")
    st.dataframe(df, hide_index=True)

    st.title('Quantidade de Atendimentos em Outubro')
    df1= conn.query('select count(*) as Quantidade_de_Atendimentos_em_Outubro from unimed.comp10 as c10;', ttl='10m')
    st.dataframe(df1,hide_index=True)

    st.title('Quantidade de Atendimentos em Novembro')
    df2= conn.query('select count(*) as Quantidade_de_Atendimentos_em_Novembro from unimed.comp11 as c11;', ttl='10m')
    st.dataframe(df2,hide_index=True)

    st.title('Quantidade de Atendimentos em Dezembro')
    df3= conn.query('select count(*) as Quantidade_de_Atendimentos_em_Dezembro from unimed.comp12 as c12;', ttl='10m')
    st.dataframe(df3,hide_index=True)

with tab2: 
    st. title ('Distância Entre Atendientos')
    df4= conn.query("""select (x."ATENDIMENTO"::time) - (x.prev::time) as diff, case when (x."ATENDIMENTO"::time) - (x.prev::time) = '00:00:00' and atendimentos_quant = 1 then null when (x."ATENDIMENTO"::time) - (x.prev::time) < '00:30:00' then 'muito_suspeito' when (x."ATENDIMENTO"::time) - (x.prev::time) < '01:00:00' then 'suspeito' else null end as status, * from (select row_number() over (partition by pep."PROFISSIONAL ", to_date(pep."DATA", 'DD/MM/YYYY')  order by to_date(pep."DATA", 'DD/MM/YYYY'),pep."ATENDIMENTO" ) as atendimentos_quant,to_date(pep."DATA", 'DD/MM/YYYY'),pep."ATENDIMENTO" ,coalesce(lag(pep."ATENDIMENTO", 1) over (partition by pep."PROFISSIONAL ", to_date(pep."DATA", 'DD/MM/YYYY') order by to_date(pep."DATA", 'DD/MM/YYYY'),pep."ATENDIMENTO"), pep."ATENDIMENTO") as prev, pep."PROFISSIONAL ", pep."PACIENTE" from unimed.base_pep as pep group by pep."PROFISSIONAL ", pep."DATA", pep."ATENDIMENTO", pep."PACIENTE" order by to_date(pep."DATA", 'DD/MM/YYYY'), pep."ATENDIMENTO", pep."PROFISSIONAL ", pep."PACIENTE") as x where case when (x."ATENDIMENTO"::time) - (x.prev::time) = '00:00:00' and atendimentos_quant = 1 then null when (x."ATENDIMENTO"::time) - (x.prev::time) < '00:30:00' then 'suspeito' when (x."ATENDIMENTO"::time) - (x.prev::time) < '01:00:00' then 'muito_suspeito' else null end is not null order by  x.to_date;""", ttl= '10m')
    df5= conn.query('select pep."PROFISSIONAL ", count(*) as quantidade from unimed.base_pep as pep group by pep."PROFISSIONAL " order by quantidade desc;', ttl='10m')
    df5_sorted = df5.sort_values(by = "quantidade", ascending=False)
    print(df5_sorted)

    # Create Plotly bar chart
    fig = px.bar(
        df5_sorted,
        x="quantidade",
        y="PROFISSIONAL ",
        title="Quantidade por Profissional"
    )

    fig.update_layout(
        yaxis=dict(autorange="reversed"),  # To keep highest on top
        height=600
    )

    st.plotly_chart(fig, use_container_width=True)

    df6= conn.query("""WITH status_categorization AS (
        SELECT 
            "DATA",
            "HORA",
            "SITUAÇÃO",
            "CONFIRMADA",
            "PACIENTE",
            "CARTEIRA",
            "PROFISSIONAL ",
            "ESPECIALIDADE",
            -- Categorização dos status
            CASE 
                -- Atendidos
                WHEN "SITUAÇÃO" = 'atendida' OR "SITUAÇÃO" ILIKE '%atend%' 
                THEN 'ATENDIDO'
                -- Cancelados
                WHEN "SITUAÇÃO" ILIKE '%cancel%' OR "SITUAÇÃO" ILIKE '%desmarca%' 
                THEN 'CANCELADO'
                -- Não comparecimento / No-show
                WHEN "SITUAÇÃO" = 'não atendida' OR "SITUAÇÃO" ILIKE '%não%' OR "SITUAÇÃO" ILIKE '%nao%' OR "SITUAÇÃO" ILIKE '%falta%'
                THEN 'NAO_COMPARECEU'
                -- Outros status
                ELSE 'OUTROS'
            END as status_categorizado,
            -- Status original para análise
            "SITUAÇÃO" as status_original
        FROM unimed.base_pep
        WHERE "DATA" IS NOT NULL 
        AND "SITUAÇÃO" IS NOT NULL
    ),
    status_summary AS (
        SELECT 
            status_categorizado,
            COUNT(*) as quantidade,
            -- Coleta exemplos de status originais por categoria
            STRING_AGG(DISTINCT status_original, ', ') as exemplos_status_original
        FROM status_categorization
        GROUP BY status_categorizado
    ),
    total_agendamentos AS (
        SELECT SUM(quantidade) as total FROM status_summary
    )

    -- Resultado principal com percentuais
    SELECT 
        s.status_categorizado,
        s.quantidade,
        ROUND((s.quantidade::numeric / t.total::numeric) * 100, 2) as percentual,
        s.exemplos_status_original
    FROM status_summary s
    CROSS JOIN total_agendamentos t
    ORDER BY s.quantidade DESC;""", ttl='10m')
    st.title('Percentual do Total de Atendimentos Agendados que Foram: Atendidos, Cancelados ou Tiveram o Não Comparecimento')

    fig4 = px.pie(df6, names='status_categorizado', values='percentual', title='Percentual de Atendimentos Agendados, Cancelados, e que Não Compareceram')

    st.plotly_chart(fig4)

with tab3: 
    df7= conn.query("""
    WITH paciente_stats AS (
        SELECT 
        
            "PACIENTE",
            "CARTEIRA",
            "NASCIMENTO",
            -- Total de agendamentos por paciente
            COUNT(*) as total_agendamentos,
            -- Total de no-shows por paciente
            SUM(CASE 
                WHEN "SITUAÇÃO" = 'não atendida' OR "SITUAÇÃO" ILIKE '%não%' OR "SITUAÇÃO" ILIKE '%nao%'
                THEN 1 
                ELSE 0 
            END) as total_no_shows,
            -- Total de atendimentos realizados
            SUM(CASE 
                WHEN "SITUAÇÃO" = 'atendida' OR "SITUAÇÃO" ILIKE '%atend%'
                THEN 1 
                ELSE 0 
            END) as total_atendidos,
            -- Primeiro agendamento
            MIN(TO_DATE("DATA", 'DD/MM/YYYY')) as primeiro_agendamento,
            -- Último agendamento
            MAX(TO_DATE("DATA", 'DD/MM/YYYY')) as ultimo_agendamento,
            -- Especialidades mais frequentes
            STRING_AGG(DISTINCT "ESPECIALIDADE", ', ') as especialidades
        FROM unimed.base_pep
        WHERE "PACIENTE ID" IS NOT NULL
        GROUP BY "PACIENTE", "CARTEIRA", "NASCIMENTO"
    ),
    paciente_taxa AS (
        SELECT 
            *,
            -- Taxa de no-show (%)
            CASE 
                WHEN total_agendamentos > 0 
                THEN ROUND((total_no_shows::numeric / total_agendamentos::numeric) * 100, 2)
                ELSE 0 
            END as taxa_no_show_percent,
            -- Taxa de comparecimento (%)
            CASE 
                WHEN total_agendamentos > 0 
                THEN ROUND((total_atendidos::numeric / total_agendamentos::numeric) * 100, 2)
                ELSE 0 
            END as taxa_comparecimento_percent,
            -- Classificação do paciente
            CASE 
                WHEN total_agendamentos = 0 THEN 'SEM DADOS'
                WHEN total_no_shows = 0 THEN 'SEM NO-SHOW'
                WHEN (total_no_shows::numeric / total_agendamentos::numeric) >= 0.8 THEN 'ALTO RISCO'
                WHEN (total_no_shows::numeric / total_agendamentos::numeric) >= 0.5 THEN 'MÉDIO RISCO'
                WHEN (total_no_shows::numeric / total_agendamentos::numeric) >= 0.2 THEN 'BAIXO RISCO'
                ELSE 'MUITO BAIXO RISCO'
            END as classificacao_risco,
            -- Período de acompanhamento em dias
            CASE 
                WHEN primeiro_agendamento IS NOT NULL AND ultimo_agendamento IS NOT NULL
                THEN ultimo_agendamento - primeiro_agendamento + 1
                ELSE 0
            END as periodo_acompanhamento_dias
        FROM paciente_stats
    )

    -- Resultado principal: pacientes ordenados por taxa de no-show
    SELECT 
    
        "PACIENTE",
        "CARTEIRA",
        total_agendamentos,
        total_no_shows,
        total_atendidos,
        taxa_no_show_percent,
        taxa_comparecimento_percent,
        classificacao_risco,
        primeiro_agendamento,
        ultimo_agendamento,
        periodo_acompanhamento_dias,
        especialidades
    FROM paciente_taxa

    ORDER BY taxa_no_show_percent DESC, total_no_shows DESC;""", ttl='10m')
    df7_sorted= df7.sort_values(by='taxa_no_show_percent', ascending= False)
    st.title('Taxa de No-Show')
    fig1 = px.bar(
    df7_sorted.head(20),
        x='taxa_no_show_percent',
        y='PACIENTE',
        title="Quantidade por Paciente (top 20)"
    )

    fig1.update_layout(
        yaxis=dict(autorange="reversed"),  # To keep highest on top
        height=600
    )

    st.plotly_chart(fig1, use_container_width=True)

    df8= conn.query("""-- Taxa de No-Show por Médico
    WITH medico_stats AS (
        SELECT 
            "PROFISSIONAL " as medico,
            "ESPECIALIDADE",
            -- Total de agendamentos por médico
            COUNT(*) as total_agendamentos,
            -- Total de no-shows por médico
            SUM(CASE 
                WHEN "SITUAÇÃO" = 'não atendida' OR "SITUAÇÃO" ILIKE '%não%' OR "SITUAÇÃO" ILIKE '%nao%'
                THEN 1 
                ELSE 0 
            END) as total_no_shows,
            -- Total de atendimentos realizados
            SUM(CASE 
                WHEN "SITUAÇÃO" = 'atendida' OR "SITUAÇÃO" ILIKE '%atend%'
                THEN 1 
                ELSE 0 
            END) as total_atendidos,
            -- Pacientes únicos atendidos
            COUNT(DISTINCT "PACIENTE ID") as pacientes_unicos,
            -- Primeiro agendamento
            MIN(TO_DATE("DATA", 'DD/MM/YYYY')) as primeiro_agendamento,
            -- Último agendamento
            MAX(TO_DATE("DATA", 'DD/MM/YYYY')) as ultimo_agendamento,
            -- Agendamentos por período
            COUNT(CASE WHEN TO_DATE("DATA", 'DD/MM/YYYY') >= CURRENT_DATE - INTERVAL '30 days' THEN 1 END) as agendamentos_ultimo_mes,
            COUNT(CASE WHEN TO_DATE("DATA", 'DD/MM/YYYY') >= CURRENT_DATE - INTERVAL '90 days' THEN 1 END) as agendamentos_ultimo_trimestre
        FROM unimed.base_pep
        WHERE "PROFISSIONAL " IS NOT NULL 
        AND TRIM("PROFISSIONAL ") != ''
        GROUP BY "PROFISSIONAL ", "ESPECIALIDADE"
    ),
    medico_taxa AS (
        SELECT 
            *,
            -- Taxa de no-show (%)
            CASE 
                WHEN total_agendamentos > 0 
                THEN ROUND((total_no_shows::numeric / total_agendamentos::numeric) * 100, 2)
                ELSE 0 
            END as taxa_no_show_percent,
            -- Taxa de comparecimento (%)
            CASE 
                WHEN total_agendamentos > 0 
                THEN ROUND((total_atendidos::numeric / total_agendamentos::numeric) * 100, 2)
                ELSE 0 
            END as taxa_comparecimento_percent,
            -- Taxa de no-show no último mês
            CASE 
                WHEN agendamentos_ultimo_mes > 0 
                THEN ROUND((
                    (SELECT COUNT(*) FROM unimed.base_pep p 
                    WHERE p."PROFISSIONAL " = medico_stats.medico
                    AND (p."SITUAÇÃO" = 'não atendida' OR p."SITUAÇÃO" ILIKE '%não%' OR p."SITUAÇÃO" ILIKE '%nao%')
                    AND TO_DATE(p."DATA", 'DD/MM/YYYY') >= CURRENT_DATE - INTERVAL '30 days'
                    )::numeric / agendamentos_ultimo_mes::numeric) * 100, 2)
                ELSE 0 
            END as taxa_no_show_ultimo_mes,
            -- Classificação do médico
            CASE 
                WHEN total_agendamentos < 10 THEN 'POUCOS DADOS'
                WHEN total_no_shows = 0 THEN 'SEM NO-SHOW'
                WHEN (total_no_shows::numeric / total_agendamentos::numeric) >= 0.4 THEN 'ALTA TAXA'
                WHEN (total_no_shows::numeric / total_agendamentos::numeric) >= 0.25 THEN 'MÉDIA TAXA'
                WHEN (total_no_shows::numeric / total_agendamentos::numeric) >= 0.1 THEN 'BAIXA TAXA'
                ELSE 'MUITO BAIXA TAXA'
            END as classificacao_no_show,
            -- Média de agendamentos por dia útil
            CASE 
                WHEN primeiro_agendamento IS NOT NULL AND ultimo_agendamento IS NOT NULL
                    AND (ultimo_agendamento - primeiro_agendamento) > 0
                THEN ROUND(total_agendamentos::numeric / (ultimo_agendamento - primeiro_agendamento + 1)::numeric, 2)
                ELSE 0
            END as media_agendamentos_dia,
            -- Período de atividade em dias
            CASE 
                WHEN primeiro_agendamento IS NOT NULL AND ultimo_agendamento IS NOT NULL
                THEN ultimo_agendamento - primeiro_agendamento + 1
                ELSE 0
            END as periodo_atividade_dias
        FROM medico_stats
    )

    -- Resultado principal: médicos ordenados por taxa de no-show
    SELECT 
        medico,
        "ESPECIALIDADE",
        total_agendamentos,
        total_no_shows,
        total_atendidos,
        pacientes_unicos,
        taxa_no_show_percent,
        taxa_comparecimento_percent,
        taxa_no_show_ultimo_mes,
        classificacao_no_show,
        agendamentos_ultimo_mes,
        agendamentos_ultimo_trimestre,
        media_agendamentos_dia,
        primeiro_agendamento,
        ultimo_agendamento,
        periodo_atividade_dias
    FROM medico_taxa
    WHERE total_agendamentos >= 5  -- Apenas médicos com pelo menos 5 agendamentos
    ORDER BY taxa_no_show_percent DESC, total_no_shows DESC;

    """, ttl='10m')


    fig2 = px.bar(
    df8,
        x='taxa_no_show_percent',
        y='medico',
        title="Quantidade por Profissional"
    )

    fig2.update_layout(
        yaxis=dict(autorange="reversed"),  # To keep highest on top
        height=600
    )

    st.plotly_chart(fig2, use_container_width=True)