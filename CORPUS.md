# Bitácora del corpus — KingsCode

Bitácora exigida en el paso 5 del enunciado. Debajo de esta bitácora sigue el registro técnico detallado del integrante A (capas, hashes, benchmark).

## 1. Inventario

Un registro por documento; coincide con `corpus_manifest.json` (171 documentos). Enlace al corpus procesado e índice: <https://github.com/IngSeb0/KingsCodeNvidia/releases/download/corpus-final/corpus_KingsCode.zip>.

| doc_id | Título | Fuente | URL | Fecha de consulta | Artículos | Áreas |
|---|---|---|---|---|---:|---|
| `codigo_civil` | Código Civil (Ley 84 de 1873; Ley 57 de 1887) | SENA | https://normograma.sena.edu.co/compilacion/docs/codigo_civil.htm | 2026-10-02 | 2683 | Derecho civil, Derecho de familia |
| `codigo_comercio` | Código de Comercio (Decreto 410 de 1971) | Función Pública | https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=41102 | 2026-10-02 | 2032 |  |
| `codigo_disciplinario` | Código General Disciplinario (Ley 1952 de 2019) | Función Pública | https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=90324 | 2026-10-02 | 278 | Derecho administrativo |
| `codigo_general_proceso` | Código General del Proceso (Ley 1564 de 2012) | Función Pública | https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=48425 | 2026-10-02 | 628 | Derecho civil, Derecho comercial y sociedades, Derecho de familia, Derecho de los mercados [competencia, consumidor, datos personales y propiedad intelectual], Derecho penal, Derecho procesal, Derecho tributario |
| `codigo_infancia` | Código de la Infancia y la Adolescencia (Ley 1098 de 2006) | Función Pública | https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=22106 | 2026-10-02 | 216 | Derecho de familia |
| `codigo_nacional_policia` | Código Nacional de Seguridad y Convivencia Ciudadana (Ley 1801 de 2016) | Función Pública | https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=80538 | 2026-10-02 | 249 | Derecho procesal |
| `codigo_penal` | Código Penal (Ley 599 de 2000) | Función Pública | https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=6388 | 2026-10-02 | 601 |  |
| `codigo_procedimiento_penal` | Código de Procedimiento Penal (Ley 906 de 2004) | Función Pública | https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=14787 | 2026-10-02 | 584 | Derecho penal, Derecho procesal |
| `codigo_sustantivo_trabajo` | Código Sustantivo del Trabajo (Decreto 2663 de 1950) | Función Pública | https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=199983 | 2026-10-02 | 491 | Derecho laboral |
| `constitucion` | Constitución Política de Colombia de 1991 | Función Pública | https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=4125 | 2026-10-02 | 446 | Derecho administrativo, Derecho comercial y sociedades, Derecho constitucional, Derecho de familia, Derecho de los mercados [competencia, consumidor, datos personales y propiedad intelectual], Derecho laboral, Derecho penal, Derecho procesal, Derecho tributario |
| `cpaca` | Código de Procedimiento Administrativo y de lo Contencioso Administrativo (Ley 1437 de 2011) | Función Pública | https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=41249 | 2026-10-02 | 321 | Derecho administrativo |
| `decreto_046_de_2024` | Decreto 046 de 2024 | Función Pública – Gestor Normativo | https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=228530 | 2026-09-29 | 0 | Derecho administrativo |
| `decreto_1082_de_2015` | Decreto 1082 de 2015 | Función Pública | https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=77653 | 2026-10-02 | 1049 | Derecho administrativo |
| `decreto_1742_de_2020` | Decreto 1742 de 2020 | Función Pública | https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=153986 | 2026-10-02 | 84 | Derecho tributario |
| `decreto_175_de_2025` | Decreto 175 de 2025 | Función Pública | https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=259629 | 2026-10-02 | 10 | Derecho tributario |
| `decreto_2067_de_1991` | Decreto 2067 de 1991 | Función Pública | https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=30150 | 2026-10-02 | 54 | Derecho constitucional |
| `decreto_2153_de_1992` | Decreto 2153 de 1992 | Función Pública | https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=38168 | 2026-10-02 | 59 | Derecho de los mercados [competencia, consumidor, datos personales y propiedad intelectual] |
| `decreto_24_de_2016` | Decreto 24 de 2016 | Función Pública | https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=67536 | 2026-10-02 | 3 | Derecho comercial y sociedades |
| `decreto_405_de_2025` | Decreto 405 de 2025 | Función Pública | https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=259517 | 2026-10-02 | 2 | Derecho laboral |
| `decreto_4334_de_2008` | Decreto 4334 de 2008 | Función Pública | https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=33747 | 2026-10-02 | 16 | Derecho comercial y sociedades |
| `decreto_4436_de_2005` | Decreto 4436 de 2005 | Función Pública | https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=18346 | 2026-10-02 | 8 | Derecho de familia |
| `decreto_4886_de_2011` | Decreto 4886 de 2011 | Función Pública | https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=66371 | 2026-10-02 | 29 | Derecho de los mercados [competencia, consumidor, datos personales y propiedad intelectual] |
| `decreto_663_de_1993` | Decreto 663 de 1993 | Función Pública | https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=1348 | 2026-10-02 | 342 | Derecho comercial y sociedades |
| `decreto_780_de_2016` | Decreto 780 de 2016 | Función Pública | https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=77813 | 2026-10-02 | 2263 | Derecho penal |
| `decreto_960_de_1970` | Decreto 960 de 1970 | Función Pública | https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=149249 | 2026-10-02 | 233 | Derecho civil |
| `estatuto_consumidor` | Estatuto del Consumidor (Ley 1480 de 2011) | Función Pública | https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=44306 | 2026-10-02 | 84 | Derecho civil, Derecho de los mercados [competencia, consumidor, datos personales y propiedad intelectual] |
| `estatuto_tributario` | Estatuto Tributario (Decreto 624 de 1989) | Función Pública | https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=6533 | 2026-10-02 | 1313 | Derecho civil, Derecho constitucional, Derecho tributario |
| `ley_1010_de_2006` | Ley 1010 de 2006 | Función Pública | https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=18843 | 2026-10-02 | 19 | Derecho laboral |
| `ley_1095_de_2006` | Ley 1095 de 2006 | Función Pública | https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=22087 | 2026-10-02 | 10 | Derecho constitucional, Derecho penal |
| `ley_1116_de_2006` | Ley 1116 de 2006 | Función Pública | https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=22657 | 2026-10-02 | 126 | Derecho comercial y sociedades, Derecho procesal |
| `ley_1150_de_2007` | Ley 1150 de 2007 | Función Pública | https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=184686 | 2026-10-02 | 33 | Derecho administrativo |
| `ley_1151_de_2007` | Ley 1151 de 2007 | Función Pública | https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=25932 | 2026-10-02 | 160 | Derecho administrativo |
| `ley_1258_de_2008` | Ley 1258 de 2008 | Función Pública | https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=34130 | 2026-10-02 | 46 | Derecho comercial y sociedades |
| `ley_1340_de_2009` | Ley 1340 de 2009 | Función Pública | https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=36912 | 2026-10-02 | 34 | Derecho de los mercados [competencia, consumidor, datos personales y propiedad intelectual] |
| `ley_137_de_1994` | Ley 137 de 1994 | Función Pública | https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=13966 | 2026-10-02 | 8 | Derecho tributario |
| `ley_1473_de_2011` | Ley 1473 de 2011 | Función Pública | https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=43236 | 2026-10-02 | 5 | Derecho tributario |
| `ley_153_de_1887` | Ley 153 de 1887 | Función Pública | https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=15805 | 2026-10-02 | 327 | Derecho civil, Derecho tributario |
| `ley_155_de_1959` | Ley 155 de 1959 | Función Pública | https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=38169 | 2026-10-02 | 20 | Derecho de los mercados [competencia, consumidor, datos personales y propiedad intelectual] |
| `ley_1562_de_2012` | Ley 1562 de 2012 | Función Pública | https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=48365 | 2026-10-02 | 33 | Derecho laboral |
| `ley_1581_de_2012` | Ley 1581 de 2012 | Función Pública | https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=49981 | 2026-10-02 | 30 | Derecho administrativo, Derecho constitucional, Derecho de los mercados [competencia, consumidor, datos personales y propiedad intelectual] |
| `ley_1607_de_2012` | Ley 1607 de 2012 | Función Pública | https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=51040 | 2026-10-02 | 248 | Derecho tributario |
| `ley_160_de_1994` | Ley 160 de 1994 | Función Pública | https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=66789 | 2026-10-02 | 114 | Derecho civil |
| `ley_1700_de_2013` | Ley 1700 de 2013 | Función Pública | https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=56283 | 2026-10-02 | 13 | Derecho comercial y sociedades |
| `ley_1755_de_2015` | Ley 1755 de 2015 | Función Pública | https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=65334 | 2026-10-02 | 23 | Derecho administrativo |
| `ley_1819_de_2016` | Ley 1819 de 2016 | Función Pública | https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=79140 | 2026-10-02 | 390 | Derecho tributario |
| `ley_1909_de_2018` | Ley 1909 de 2018 | Función Pública | https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=87302 | 2026-10-02 | 32 | Derecho constitucional |
| `ley_2114_de_2021` | Ley 2114 de 2021 | Función Pública | https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=167967 | 2026-10-02 | 6 | Derecho laboral |
| `ley_2141_de_2021` | Ley 2141 de 2021 | Función Pública | https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=168351 | 2026-10-02 | 3 | Derecho constitucional, Derecho laboral |
| `ley_2157_de_2021` | Ley 2157 de 2021 | Función Pública | https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=173246 | 2026-10-02 | 3 | Derecho de los mercados [competencia, consumidor, datos personales y propiedad intelectual] |
| `ley_2160_de_2021` | Ley 2160 de 2021 | Función Pública | https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=173787 | 2026-10-02 | 5 | Derecho administrativo |
| `ley_2220_de_2022` | Ley 2220 de 2022 | Función Pública | https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=188766 | 2026-10-02 | 147 | Derecho civil, Derecho procesal |
| `ley_2251_de_2022` | Ley 2251 de 2022 | Función Pública | https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=189806 | 2026-10-02 | 24 | Derecho civil |
| `ley_2437_de_2024` | Ley 2437 de 2024 | Función Pública | https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=256656 | 2026-10-02 | 21 | Derecho civil, Derecho procesal |
| `ley_2452_de_2025` | Ley 2452 de 2025 | Función Pública | https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=259639 | 2026-10-02 | 331 | Derecho laboral |
| `ley_2466_de_2025` | Ley 2466 de 2025 | Función Pública | https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=260676 | 2026-10-02 | 70 | Derecho laboral |
| `ley_256_de_1996` | Ley 256 de 1996 | Función Pública | https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=38871 | 2026-10-02 | 33 | Derecho de los mercados [competencia, consumidor, datos personales y propiedad intelectual] |
| `ley_29_de_1982` | Ley 29 de 1982 | Función Pública | https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=256 | 2026-10-02 | 11 | Derecho de familia |
| `ley_472_de_1998` | Ley 472 de 1998 | Función Pública | https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=188 | 2026-10-02 | 87 | Derecho constitucional, Derecho administrativo |
| `ley_50_de_1990` | Ley 50 de 1990 | Función Pública | https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=281 | 2026-10-02 | 116 | Derecho laboral |
| `ley_527_de_1999` | Ley 527 de 1999 | Función Pública | https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=4276 | 2026-10-02 | 47 | Derecho comercial y sociedades |
| `ley_54_de_1990` | Ley 54 de 1990 | Función Pública | https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=30896 | 2026-10-02 | 8 | Derecho de familia |
| `ley_600_de_2000` | Ley 600 de 2000 | Función Pública | https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=6389 | 2026-10-02 | 475 | Derecho penal |
| `ley_640_de_2001` | Ley 640 de 2001 | Función Pública | https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=6059 | 2026-10-02 | 50 | Derecho de los mercados [competencia, consumidor, datos personales y propiedad intelectual] |
| `ley_678_de_2001` | Ley 678 de 2001 | Función Pública | https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=4164 | 2026-10-02 | 32 | Derecho procesal |
| `ley_721_de_2001` | Ley 721 de 2001 | Función Pública | https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=9565 | 2026-10-02 | 8 | Derecho de familia |
| `ley_75_de_1968` | Ley 75 de 1968 | Función Pública | https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=4828 | 2026-10-02 | 67 | Derecho de familia |
| `ley_769_de_2002` | Ley 769 de 2002 | Función Pública | https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=5557 | 2026-10-02 | 177 | Derecho civil |
| `ley_80_de_1993` | Ley 80 de 1993 | Función Pública | https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=304 | 2026-10-02 | 88 | Derecho administrativo, Derecho laboral |
| `ley_820_de_2003` | Ley 820 de 2003 | Función Pública | https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=8738 | 2026-10-02 | 43 | Derecho comercial y sociedades |
| `ley_979_de_2005` | Ley 979 de 2005 | Función Pública | https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=30898 | 2026-10-02 | 5 | Derecho de familia |
| `sentencia_c_1033_de_2002` | Sentencia C-1033 de 2002 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2002/C-1033-02.htm | 2026-10-02 | 0 | Derecho de familia |
| `sentencia_c_106_de_2018` | Sentencia C-106 de 2018 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2018/C-106-18.htm | 2026-10-02 | 0 | Derecho constitucional |
| `sentencia_c_117_de_2018` | Sentencia C-117 de 2018 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2018/C-117-18.htm | 2026-10-02 | 0 | Derecho tributario |
| `sentencia_c_1189_de_2000` | Sentencia C-1189 de 2000 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2000/C-1189-00.htm | 2026-10-02 | 0 | Derecho penal |
| `sentencia_c_127_de_2011` | Sentencia C-127 de 2011 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2011/C-127-11.htm | 2026-10-02 | 0 | Derecho constitucional |
| `sentencia_c_131_de_2018` | Sentencia C-131 de 2018 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2018/C-131-18.htm | 2026-10-02 | 0 | Derecho de familia |
| `sentencia_c_134_de_2019` | Sentencia C-134 de 2019 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2019/C-134-19.htm | 2026-10-02 | 0 | Derecho constitucional, Derecho de familia |
| `sentencia_c_145_de_2018` | Sentencia C-145 de 2018 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2018/C-145-18.htm | 2026-10-02 | 0 | Derecho comercial y sociedades |
| `sentencia_c_145_de_2020` | Sentencia C-145 de 2020 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2020/C-145-20.htm | 2026-10-02 | 0 | Derecho constitucional |
| `sentencia_c_149_de_1993` | Sentencia C-149 de 1993 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/1993/C-149-93.htm | 2026-10-02 | 0 | Derecho constitucional |
| `sentencia_c_15_de_2018` | Sentencia C-15 de 2018 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2018/C-015-18.htm | 2026-10-02 | 0 | Derecho constitucional, Derecho penal |
| `sentencia_c_164_de_2022` | Sentencia C-164 de 2022 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2022/C-164-22.htm | 2026-10-02 | 0 | Derecho constitucional, Derecho penal |
| `sentencia_c_170_de_2004` | Sentencia C-170 de 2004 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2004/C-170-04.htm | 2026-10-02 | 0 | Derecho laboral |
| `sentencia_c_183_de_2025` | Sentencia C-183 de 2025 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2025/C-183-25.htm | 2026-10-02 | 0 | Derecho civil |
| `sentencia_c_201_de_2002` | Sentencia C-201 de 2002 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2002/C-201-02.htm | 2026-10-02 | 0 | Derecho laboral |
| `sentencia_c_207_de_2019` | Sentencia C-207 de 2019 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2019/C-207-19.htm | 2026-10-02 | 0 | Derecho administrativo |
| `sentencia_c_225_de_1995` | Sentencia C-225 de 1995 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/1995/C-225-95.htm | 2026-10-02 | 0 | Derecho constitucional |
| `sentencia_c_22_de_1996` | Sentencia C-22 de 1996 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/1996/C-022-96.htm | 2026-10-02 | 0 | Derecho constitucional |
| `sentencia_c_233_de_2021` | Sentencia C-233 de 2021 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2021/C-233-21.htm | 2026-10-02 | 0 | Derecho constitucional |
| `sentencia_c_239_de_1997` | Sentencia C-239 de 1997 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/1997/C-239-97.htm | 2026-10-02 | 0 | Derecho constitucional |
| `sentencia_c_259_de_2015` | Sentencia C-259 de 2015 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2015/C-259-15.htm | 2026-10-02 | 0 | Derecho administrativo, Derecho procesal |
| `sentencia_c_276_de_2025` | Sentencia C-276 de 2025 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2025/C-276-25.htm | 2026-10-02 | 0 | Derecho comercial y sociedades |
| `sentencia_c_332_de_2025` | Sentencia C-332 de 2025 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2025/C-332-25.htm | 2026-10-02 | 0 | Derecho constitucional |
| `sentencia_c_335_de_2008` | Sentencia C-335 de 2008 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2008/C-335-08.htm | 2026-10-02 | 0 | Derecho penal |
| `sentencia_c_345_de_2017` | Sentencia C-345 de 2017 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2017/C-345-17.htm | 2026-10-02 | 0 | Derecho civil |
| `sentencia_c_355_de_2006` | Sentencia C-355 de 2006 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2006/C-355-06.htm | 2026-10-02 | 0 | Derecho constitucional, Derecho penal |
| `sentencia_c_35_de_2009` | Sentencia C-35 de 2009 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2009/C-035-09.htm | 2026-10-02 | 0 | Derecho tributario |
| `sentencia_c_389_de_2023` | Sentencia C-389 de 2023 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2023/C-389-23.htm | 2026-10-02 | 0 | Derecho tributario |
| `sentencia_c_394_de_2017` | Sentencia C-394 de 2017 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2017/C-394-17.htm | 2026-10-02 | 0 | Derecho constitucional, Derecho de familia |
| `sentencia_c_39_de_2025` | Sentencia C-39 de 2025 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2025/C-039-25.htm | 2026-10-02 | 0 | Derecho de familia |
| `sentencia_c_413_de_1996` | Sentencia C-413 de 1996 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/1996/C-413-96.htm | 2026-10-02 | 0 | Derecho tributario |
| `sentencia_c_431_de_2001` | Sentencia C-431 de 2001 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2001/C-431-01.htm | 2026-10-02 | 0 | Derecho constitucional, Derecho penal |
| `sentencia_c_459_de_2023` | Sentencia C-459 de 2023 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2023/C-459-23.htm | 2026-10-02 | 0 | Derecho constitucional |
| `sentencia_c_468_de_2024` | Sentencia C-468 de 2024 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2024/C-468-24.htm | 2026-10-02 | 0 | Derecho constitucional |
| `sentencia_c_486_de_1993` | Sentencia C-486 de 1993 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/1993/C-486-93.htm | 2026-10-02 | 0 | Derecho comercial y sociedades |
| `sentencia_c_4_de_1998` | Sentencia C-4 de 1998 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/1998/C-004-98.htm | 2026-10-02 | 0 | Derecho de familia |
| `sentencia_c_500_de_2024` | Sentencia C-500 de 2024 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2024/C-500-24.htm | 2026-10-02 | 0 | Derecho procesal, Derecho tributario |
| `sentencia_c_507_de_2004` | Sentencia C-507 de 2004 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2004/C-507-04.htm | 2026-10-02 | 0 | Derecho de familia |
| `sentencia_c_533_de_2000` | Sentencia C-533 de 2000 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2000/C-533-00.htm | 2026-10-02 | 0 | Derecho de familia |
| `sentencia_c_535_de_2002` | Sentencia C-535 de 2002 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2002/C-535-02.htm | 2026-10-02 | 0 | Derecho laboral |
| `sentencia_c_537_de_1995` | Sentencia C-537 de 1995 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/1995/C-537-95.htm | 2026-10-02 | 0 | Derecho tributario |
| `sentencia_c_540_de_2023` | Sentencia C-540 de 2023 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2023/C-540-23.htm | 2026-10-02 | 0 | Derecho tributario |
| `sentencia_c_55_de_2022` | Sentencia C-55 de 2022 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2022/C-055-22.htm | 2026-10-02 | 0 | Derecho constitucional, Derecho penal |
| `sentencia_c_582_de_1999` | Sentencia C-582 de 1999 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/1999/C-582-99.htm | 2026-10-02 | 0 | Derecho constitucional |
| `sentencia_c_683_de_2015` | Sentencia C-683 de 2015 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2015/C-683-15.htm | 2026-10-02 | 0 | Derecho de familia |
| `sentencia_c_700_de_1999` | Sentencia C-700 de 1999 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/1999/C-700-99.htm | 2026-10-02 | 0 | Derecho constitucional |
| `sentencia_c_746_de_2011` | Sentencia C-746 de 2011 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2011/C-746-11.htm | 2026-10-02 | 0 | Derecho constitucional, Derecho de familia |
| `sentencia_c_748_de_2011` | Sentencia C-748 de 2011 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2011/C-748-11.htm | 2026-10-02 | 0 | Derecho civil, Derecho de los mercados [competencia, consumidor, datos personales y propiedad intelectual] |
| `sentencia_c_80_de_2025` | Sentencia C-80 de 2025 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2025/C-080-25.htm | 2026-10-02 | 0 | Derecho de los mercados [competencia, consumidor, datos personales y propiedad intelectual] |
| `sentencia_c_891_de_2012` | Sentencia C-891 de 2012 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2012/C-891-12.htm | 2026-10-02 | 0 | Derecho tributario |
| `sentencia_c_94_de_2021` | Sentencia C-94 de 2021 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2021/C-094-21.htm | 2026-10-02 | 0 | Derecho constitucional |
| `sentencia_c_964_de_2003` | Sentencia C-964 de 2003 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2003/C-964-03.htm | 2026-10-02 | 0 | Derecho de familia |
| `sentencia_c_96_de_2024` | Sentencia C-96 de 2024 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2024/C-096-24.htm | 2026-10-02 | 0 | Derecho de familia |
| `sentencia_c_985_de_2010` | Sentencia C-985 de 2010 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2010/C-985-10.htm | 2026-10-02 | 0 | Derecho de familia |
| `sentencia_sl_3385_de_2022` | Sentencia SL-3385 de 2022 | Corte Suprema de Justicia | https://cortesuprema.gov.co/corte/wp-content/uploads/relatorias/la/bnov2022/SL3385-2022.pdf | 2026-10-02 | 0 | Derecho laboral |
| `sentencia_sl_648_de_2018` | Sentencia SL-648 de 2018 | Corte Suprema de Justicia | https://www.cortesuprema.gov.co/corte/wp-content/uploads/relatorias/la/bmar2018/SL648-2018.pdf | 2026-09-29 | 0 | Derecho laboral |
| `sentencia_sp_1167_de_2022` | Sentencia SP-1167 de 2022 | Corte Suprema de Justicia | https://cortesuprema.gov.co/corte/wp-content/uploads/relatorias/pe/b1may2022/SP1167-2022%2857957%29.pdf | 2026-09-29 | 0 | Derecho penal |
| `sentencia_sp_1680_de_2022` | Sentencia SP-1680 de 2022 | Corte Suprema de Justicia | https://cortesuprema.gov.co/corte/wp-content/uploads/relatorias/pe/b1may2022/SP1680-2022%2860875%29.pdf | 2026-09-29 | 0 | Derecho penal |
| `sentencia_sp_1945_de_2019` | Sentencia SP-1945 de 2019 | Corte Suprema de Justicia | https://www.cortesuprema.gov.co/corte/wp-content/uploads/relatorias/pe/b1ago2019/SP1945-2019%2850523%29.PDF | 2026-09-29 | 0 |  |
| `sentencia_su_111_de_2025` | Sentencia SU-111 de 2025 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2025/SU111-25.htm | 2026-10-02 | 0 | Derecho laboral |
| `sentencia_su_11_de_2020` | Sentencia SU-11 de 2020 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2020/SU011-20.htm | 2026-10-02 | 0 | Derecho administrativo |
| `sentencia_su_138_de_2024` | Sentencia SU-138 de 2024 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2024/SU138-24.htm | 2026-10-02 | 0 | Derecho civil |
| `sentencia_su_149_de_2021` | Sentencia SU-149 de 2021 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2021/SU149-21.htm | 2026-10-02 | 0 | Derecho laboral |
| `sentencia_su_16_de_2020` | Sentencia SU-16 de 2020 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2020/SU016-20.htm | 2026-10-02 | 0 | Derecho constitucional |
| `sentencia_su_207_de_2022` | Sentencia SU-207 de 2022 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2022/SU207-22.htm | 2026-10-02 | 0 | Derecho civil |
| `sentencia_su_214_de_2016` | Sentencia SU-214 de 2016 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2016/SU214-16.htm | 2026-10-02 | 0 | Derecho de familia |
| `sentencia_su_240_de_2015` | Sentencia SU-240 de 2015 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2015/SU240-15.htm | 2026-10-02 | 0 | Derecho administrativo |
| `sentencia_su_277_de_2025` | Sentencia SU-277 de 2025 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2025/SU277-25.htm | 2026-10-02 | 0 | Derecho administrativo |
| `sentencia_su_27_de_2021` | Sentencia SU-27 de 2021 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2021/SU027-21.htm | 2026-10-02 | 0 | Derecho laboral |
| `sentencia_su_296_de_2023` | Sentencia SU-296 de 2023 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2023/SU296-23.htm | 2026-10-02 | 0 | Derecho laboral |
| `sentencia_su_315_de_2025` | Sentencia SU-315 de 2025 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2025/SU315-25.htm | 2026-10-02 | 0 | Derecho civil |
| `sentencia_su_380_de_2021` | Sentencia SU-380 de 2021 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2021/SU380-21.htm | 2026-10-02 | 0 | Derecho civil |
| `sentencia_su_396_de_2024` | Sentencia SU-396 de 2024 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2024/SU396-24.htm | 2026-10-02 | 0 | Derecho laboral |
| `sentencia_su_425_de_2025` | Sentencia SU-425 de 2025 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2025/SU425-25.htm | 2026-10-02 | 0 | Derecho civil |
| `sentencia_su_429_de_2024` | Sentencia SU-429 de 2024 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2024/SU429-24.htm | 2026-10-02 | 0 | Derecho penal |
| `sentencia_su_431_de_2015` | Sentencia SU-431 de 2015 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2015/SU431-15.htm | 2026-10-02 | 0 | Derecho civil |
| `sentencia_su_455_de_2020` | Sentencia SU-455 de 2020 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2020/SU455-20.htm | 2026-10-02 | 0 | Derecho civil |
| `sentencia_su_500_de_2015` | Sentencia SU-500 de 2015 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2015/SU500-15.htm | 2026-10-02 | 0 | Derecho civil |
| `sentencia_su_566_de_2015` | Sentencia SU-566 de 2015 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2015/SU566-15.htm | 2026-10-02 | 0 | Derecho administrativo |
| `sentencia_t_1001_de_2001` | Sentencia T-1001 de 2001 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2001/T-1001-01.htm | 2026-10-02 | 0 | Derecho constitucional |
| `sentencia_t_1059_de_2001` | Sentencia T-1059 de 2001 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2001/T-1059-01.htm | 2026-10-02 | 0 | Derecho laboral |
| `sentencia_t_1096_de_2008` | Sentencia T-1096 de 2008 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2008/T-1096-08.htm | 2026-10-02 | 0 | Derecho de familia |
| `sentencia_t_145_de_2016` | Sentencia T-145 de 2016 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2016/T-145-16.htm | 2026-10-02 | 0 | Derecho laboral |
| `sentencia_t_230_de_2023` | Sentencia T-230 de 2023 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2023/T-230-23.htm | 2026-10-02 | 0 | Derecho constitucional |
| `sentencia_t_232_de_2025` | Sentencia T-232 de 2025 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2025/T-232-25.htm | 2026-10-02 | 0 | Derecho de familia |
| `sentencia_t_243_de_2018` | Sentencia T-243 de 2018 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2018/T-243-18.htm | 2026-10-02 | 0 | Derecho laboral |
| `sentencia_t_262_de_2025` | Sentencia T-262 de 2025 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2025/T-262-25.htm | 2026-10-02 | 0 | Derecho constitucional |
| `sentencia_t_26_de_2025` | Sentencia T-26 de 2025 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2025/T-026-25.htm | 2026-10-02 | 0 | Derecho civil |
| `sentencia_t_323_de_2024` | Sentencia T-323 de 2024 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2024/T-323-24.htm | 2026-10-02 | 0 | Derecho constitucional |
| `sentencia_t_325_de_2025` | Sentencia T-325 de 2025 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2025/T-325-25.htm | 2026-10-02 | 0 | Derecho constitucional |
| `sentencia_t_350_de_2025` | Sentencia T-350 de 2025 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2025/T-350-25.htm | 2026-10-02 | 0 | Derecho de familia |
| `sentencia_t_429_de_2011` | Sentencia T-429 de 2011 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2011/T-429-11.htm | 2026-10-02 | 0 | Derecho constitucional |
| `sentencia_t_445_de_2024` | Sentencia T-445 de 2024 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2024/T-445-24.htm | 2026-10-02 | 0 | Derecho constitucional |
| `sentencia_t_4_de_2026` | Sentencia T-4 de 2026 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2026/T-004-26.htm | 2026-10-02 | 0 | Derecho civil |
| `sentencia_t_547_de_2017` | Sentencia T-547 de 2017 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2017/T-547-17.htm | 2026-10-02 | 0 | Derecho constitucional, Derecho laboral |
| `sentencia_t_67_de_2025` | Sentencia T-67 de 2025 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2025/T-067-25.htm | 2026-10-02 | 0 | Derecho constitucional |
| `sentencia_t_71_de_2016` | Sentencia T-71 de 2016 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2016/T-071-16.htm | 2026-10-02 | 0 | Derecho de familia |
| `sentencia_t_760_de_2008` | Sentencia T-760 de 2008 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2008/T-760-08.htm | 2026-10-02 | 0 | Derecho administrativo, Derecho constitucional |
| `sentencia_t_77_de_2025` | Sentencia T-77 de 2025 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2025/T-077-25.htm | 2026-10-02 | 0 | Derecho de familia |
| `sentencia_t_925_de_2014` | Sentencia T-925 de 2014 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2014/T-925-14.htm | 2026-10-02 | 0 | Derecho constitucional |
| `sentencia_t_970_de_2014` | Sentencia T-970 de 2014 | Corte Constitucional | https://www.corteconstitucional.gov.co/relatoria/2014/T-970-14.htm | 2026-10-02 | 0 | Derecho constitucional |

**Totales**

| Métrica | Valor |
|---|---:|
| Documentos incorporados | 171 |
| Artículos (o unidades de sentencia) | 17.606 |
| Fragmentos en el índice | 26.665 (26.167 recuperables; 498 encabezados o duplicados excluidos) |
| Tamaño del corpus procesado | 40,8 MB de texto limpio; `corpus_KingsCode.zip` 105,7 MB con índices |

## 2. Criterio de selección

El banco cubre diez áreas del derecho colombiano. Priorizamos, en este orden:

1. La Constitución y los códigos que concentran la mayoría de las preguntas: Civil, Comercio, General del Proceso, Penal, Procedimiento Penal, Sustantivo del Trabajo, CPACA, Infancia, Policía y Disciplinario.
2. Las leyes y decretos reglamentarios más citados en esas áreas: contratación estatal, tributario, consumidor, protección de datos, acoso laboral, insolvencia y competencia, entre otros.
3. Sentencias de constitucionalidad, tutela y unificación de la Corte Constitucional y de la Corte Suprema.

Cada ampliación se decidió por análisis de fallas en la muestra oficial y en un benchmark interno sin respuestas del banco. Por ejemplo, se añadieron la Ley 472 de 1998 y sentencias de unificación. Nunca se indexaron las preguntas ni las respuestas esperadas.

| Área | Documentos |
|---|---:|
| Derecho constitucional | 43 |
| Derecho de familia | 29 |
| Derecho laboral | 25 |
| Derecho civil | 24 |
| Derecho administrativo | 19 |
| Derecho tributario | 18 |
| Derecho penal | 16 |
| Derecho comercial y sociedades | 13 |
| Derecho de los mercados [competencia, consumidor, datos personales y propiedad intelectual] | 13 |
| Derecho procesal | 10 |

| Fuente | Documentos |
|---|---:|
| Corte Constitucional | 96 |
| Función Pública | 68 |
| Corte Suprema de Justicia | 5 |
| SENA | 1 |
| Función Pública – Gestor Normativo | 1 |

**Vacíos conocidos.** Hay poca jurisprudencia del Consejo de Estado: un candidato con tres sentencias de unificación no pasó la prueba pareada de recuperación. No hay derecho internacional. La vigencia no está certificada artículo por artículo.

## 3. Método de ingesta y limpieza

1. **Descarga** desde la URL oficial con TLS verificado (`tools/member_a.py acquire`, fuentes en `config/sources.json`). Se registran el estado HTTP, el tipo de contenido, la fecha y el SHA-256 del archivo crudo.
2. **Limpieza** del HTML o PDF a texto plano. Se conservan las notas de vigencia de la fuente y se eliminan la navegación y los elementos repetidos.
3. **Segmentación estructural** (`legal-blocks-1.2`): un fragmento por artículo, o por unidad de sentencia. Cada fragmento lleva norma, número, año, jerarquía (libro, título, capítulo), *offsets* en el texto limpio, áreas y URL.
4. **Índices:**
   - BM25 por artículo (`bm25.json`).
   - Índice vectorial exacto Qwen3-Embedding-0.6B (`dense.npy`, 1.024 dimensiones).
   - Grafo normativo (59 mil nodos y 75 mil aristas *modifica / deroga / remite / reglamenta*).
5. **Reconstrucción:** `python tools/member_a.py acquire` + `reproduce`, o restauración del snapshot verificado. Los hashes están en las secciones de abajo.

## 4. Evolución del puntaje

Medido con `scripts/evaluate.py` sobre la muestra de 50 preguntas, sin RAGAS. Una variable por corrida.

| Corrida | Cambio | Puntaje /50 |
|---|---|---:|
| 1 | Primera versión (BM25, Qwen3-8B) | 26,63 |
| 2 | Una consulta por opción en selección múltiple | 30,41 |
| 3 | Guarda y reparación de citas | 35,18 |
| 4 | Citas completadas y verificadas | 36,93 |
| 5 | Prompt v4 | 37,46 |
| 6 | Prompt v6 (método jurídico) | 38,08 |
| 7 | Corpus ampliado (v0.1 + v0.2 + adiciones), v4 | 39,02 |
| 8 | v6 + búsqueda semántica en texto libre | 38,84 |

## 5. Licencia

- El procesamiento propio (limpieza, segmentación, metadatos, índices y grafo) se publica bajo **CC BY 4.0**.
- Los textos normativos y jurisprudenciales son documentos oficiales públicos de Colombia. Su URL y su fecha de consulta están en el inventario.

---

# Registro técnico del corpus (integrante A)

Snapshot `corpus-v0.1`, parser `legal-blocks-1.2`. Estado: baseline local previo a integración GPU y freeze competitivo.

## Capa v0.6 (metadatos + recuperación)

La v0.6 añade una capa de derivación determinista sobre el mismo snapshot
`corpus-v0.1`, **sin reconstruir ni modificar** los artefactos del corpus: el
build se reproduce byte a byte con los mismos hashes. Aporta:

- Identidad canónica independiente de la URL: `canonical_document_id`
  (`ley:1564:2012`, `decreto:410:1971`, `codigo_civil`, `constitucion:1991`,
  `corte_constitucional:c355:2006`, `corte_suprema:sl3385:2022`) y
  `canonical_fragment_id` (`ley:1564:2012:articulo:391`), en espacios de nombres
  separados; variantes históricas y encabezados repetidos se conservan distintos.
- Metadatos temporales conservadores (`status_assertion` con
  `current/historical/repealed/modified/unknown`, por defecto `unknown`) y
  `content_hash` del cuerpo semántico (excluye el encabezado de norma/jerarquía).
- Clasificación de los 28 objetivos de adquisición no resueltos
  (`resolved/not_found/ambiguous/source_unavailable/identifier_suspect`) sin
  sustituir identificadores.
- Deduplicación/diversificación configurable (apta para ablación, no activa por
  defecto) que conserva la procedencia de espejos.
- Taxonomía de fallos de recuperación y `document_mismatch_rate` (definición
  propia; no se afirma equivalencia con una métrica académica DRM).
- Experimentos opcionales R6/R7/R8 sobre la API pública, sin cambiar la ruta por
  defecto ni las métricas de R0–R5.

Reportes: `reports/corpus_coverage_v06.json`,
`reports/acquisition_backlog_v06.json`,
`reports/retrieval_failures_bm25_<modo>.json`. Ver `docs/MEMBER_A_RUNBOOK.md`.
El conteo de documentos no se usa como proxy de calidad.

## Inventario medido

- 163 documentos oficiales adquiridos y parseados; 28 objetivos pendientes, registrados sin sustituir su identidad.
- 26558 pasajes conservados; 26060 elegibles para recuperación. Los demás son texto histórico explícito o numeraciones ambiguas.
- 59236 nodos y 75380 relaciones con evidencia textual verificable.
- Inventario original: 186 objetivos oficiales; configuración ampliada a 191 fuentes objetivo, sin indexar preguntas, respuestas ni etiquetas de evaluación.

| Institución | Documentos |
|---|---:|
| Comunidad Andina | 1 |
| Corte Constitucional | 93 |
| Corte Suprema de Justicia | 1 |
| Función Pública | 67 |
| SENA | 1 |

| Área declarada en inventario | Documentos |
|---|---:|
| Derecho administrativo | 16 |
| Derecho civil | 24 |
| Derecho comercial y sociedades | 14 |
| Derecho constitucional | 40 |
| Derecho de familia | 29 |
| Derecho de los mercados [competencia, consumidor, datos personales y propiedad intelectual] | 14 |
| Derecho laboral | 24 |
| Derecho penal | 14 |
| Derecho procesal | 10 |
| Derecho tributario | 18 |

Las áreas pueden solaparse; son metadatos de inventario y no juicios de relevancia de cada pasaje.

## Procedencia y procesamiento

Cada documento conserva URL solicitada/final, institución, instante UTC de consulta, HTTP 200, TLS verificado, bytes originales y SHA-256. El manifest registra raw, clean y sus hashes. Se conservan originales en `corpus/raw`, texto en `corpus/clean`, pasajes en `corpus/passages.jsonl` y grafo en `corpus/graph`.

El parser extrae bloques del contenedor jurídico y conserva texto fuera de párrafos. El artículo es la unidad principal, con jerarquía y fragmentación por párrafo/oración cuando supera 3.600 caracteres. Los encabezados se incluyen como `text_prefix`; el resto corresponde exactamente a `[clean_start:clean_end]` en caracteres Unicode del clean. PDF: se registran páginas; Decisión CAN 486 omite la portada sin texto utilizable, pero conserva el documento original completo. Se revisaron visualmente páginas de ambos PDF.

Las reformas citadas se mantienen bajo el artículo reformador cuando la estructura es inequívoca. Los grupos con números de artículo repetidos quedan conservados y excluidos de los índices: no se escoge automáticamente una versión ni se atribuye un anexo a la norma principal. `retrieval_eligible` e `index_exclusion_reasons` explican la exclusión. `is_current_text=null` significa vigencia no certificada. Se requiere revisar estas ambigüedades antes del freeze.

El grafo representa norma/sentencia, sección, artículo, parágrafo y numeral. Genera `CONTIENE`, `CITA`, `REMITE_A` y patrones explícitos de `MODIFICA`/`DEROGA`. Los demás tipos y tags jurídicos quedan reservados; no se infieren relaciones jurídicas por similitud. Nodos externos sin texto no se recuperan como evidencia.

## Retrieval y resultados de desarrollo

BM25 usa k1=1,2 y b=0,75, normalización de acentos y desempate estable. La API pública es `retrieve(question, k=8, graph_mode="auto")`. RRF, dense y reranker están implementados con Qwen3 abierto de 0,6B y commits fijos. La prueba neuronal usa pesos reales sobre dos pasajes oficiales; el índice denso completo y su benchmark quedan pendientes para la 4090.

De las 50 preguntas, 41 tienen referencias extraíbles y 36 cuentan con todas sus referencias en el índice. Cobertura macro de referencias: 90.89%. Las otras preguntas no cuentan como aciertos automáticos.

| BM25 / grafo | Recall@1 | Recall@3 | Recall@5 | Recall@10 | MRR@10 | nDCG@10 |
|---|---:|---:|---:|---:|---:|---:|
| OFF | 0.2317 | 0.3423 | 0.4398 | 0.5252 | 0.3401 | 0.3694 |
| AUTO | 0.2317 | 0.3423 | 0.4398 | 0.5252 | 0.3401 | 0.3694 |
| ON | 0.2561 | 0.3911 | 0.4154 | 0.5374 | 0.3681 | 0.3921 |

La métrica compara identidad canónica de norma y artículo, no menciones a otra norma. `legal_basis` es un proxy ruidoso, no relevancia jurídica validada ni score oficial end-to-end. Se conservan etiquetas ambiguas originales (incluidos IDs 58 y 308) en la auditoría, separada del índice. Los desgloses por área/formato, latencias y predicciones están en `reports/retrieval_bm25*.json*`. AUTO no se activó en este sample: su igualdad con OFF no prueba beneficio del routing. ON es una ablation forzada, no la nueva política por defecto.

## Reproducción y verificación

Consultar [runbook](docs/MEMBER_A_RUNBOOK.md) para comandos, integración con B y pruebas. `tools/member_a.py reproduce` reconstruye desde el snapshot raw sin red. Volver a descargar puede producir versiones nuevas y requiere otro freeze. `tools/verify_member_a_second.py` reconstruye en otra carpeta, compara hashes byte a byte y recalcula métricas y rankings independientemente. Los reportes de verificación identifican el hash que comprobaron.

Los 19 archivos oficiales se preservan. No se han generado submissions ni se afirma score del decoder. El equipo aún debe integrar B, ejecutar benchmark neuronal completo, revisar vigencia y exclusiones, escoger la licencia del procesamiento propio y publicar el paquete final. El acceso público a las fuentes no implica una licencia uniforme de redistribución. `enlace_nube=null`: corpus local, no publicado.

## Hashes del snapshot

| Artefacto | SHA-256 |
|---|---|
| `passages.jsonl` | `3b2b7a7beae2abe0abd14480be887a86ad933902c9735a21e02719a12daac3c0` |
| `graph/nodes.jsonl` | `7c8af359cb1ac8de13872e01d2d0faf18218d24e1e2af326529f4a11c0a39aaa` |
| `graph/edges.jsonl` | `6002fdcdbb4fb673761cb2dbe949db2502306809f2179e4133d8f40c286ff634` |
| `index/bm25.json` | `aa6b40c5e70f88513a7cde7e9ca96a15d1d40088c538668087700b9b46de005b` |

## Fuentes completas

Los hashes, fechas exactas, números, años, cuerpos canónicos y rutas están en [corpus_manifest.json](corpus_manifest.json).

| Documento | Institución | Pasajes | Indexados | Fecha UTC | Fuente |
|---|---|---:|---:|---|---|
| Código Civil (Ley 84 de 1873; Ley 57 de 1887) | SENA | 2683 | 2683 | 2026-09-28 | [Oficial](https://normograma.sena.edu.co/compilacion/docs/codigo_civil.htm) |
| Código de Comercio (Decreto 410 de 1971) | Función Pública | 2115 | 2030 | 2026-09-28 | [Oficial](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=41102) |
| Código General Disciplinario (Ley 1952 de 2019) | Función Pública | 282 | 282 | 2026-09-28 | [Oficial](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=90324) |
| Código General del Proceso (Ley 1564 de 2012) | Función Pública | 659 | 659 | 2026-09-28 | [Oficial](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=48425) |
| Código de la Infancia y la Adolescencia (Ley 1098 de 2006) | Función Pública | 225 | 225 | 2026-09-28 | [Oficial](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=22106) |
| Código Nacional de Seguridad y Convivencia Ciudadana (Ley 1801 de 2016) | Función Pública | 274 | 274 | 2026-09-28 | [Oficial](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=80538) |
| Código Penal (Ley 599 de 2000) | Función Pública | 608 | 606 | 2026-09-28 | [Oficial](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=6388) |
| Código de Procedimiento Penal (Ley 906 de 2004) | Función Pública | 595 | 588 | 2026-09-28 | [Oficial](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=14787) |
| Código Sustantivo del Trabajo (Decreto 2663 de 1950) | Función Pública | 504 | 504 | 2026-09-28 | [Oficial](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=199983) |
| Constitución Política de Colombia de 1991 | Función Pública | 615 | 462 | 2026-09-28 | [Oficial](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=4125) |
| Código de Procedimiento Administrativo y de lo Contencioso Administrativo (Ley 1437 de 2011) | Función Pública | 338 | 338 | 2026-09-28 | [Oficial](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=41249) |
| Decisión Andina 486 de 2000 | Comunidad Andina | 280 | 280 | 2026-09-28 | [Oficial](https://www.comunidadandina.org/StaticFiles/DocOf/DEC486.pdf) |
| Decreto 1082 de 2015 | Función Pública | 1120 | 1082 | 2026-09-28 | [Oficial](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=77653) |
| Decreto 1742 de 2020 | Función Pública | 111 | 111 | 2026-09-28 | [Oficial](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=153986) |
| Decreto 175 de 2025 | Función Pública | 12 | 12 | 2026-09-28 | [Oficial](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=259629) |
| Decreto 2067 de 1991 | Función Pública | 54 | 54 | 2026-09-28 | [Oficial](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=30150) |
| Decreto 2153 de 1992 | Función Pública | 65 | 60 | 2026-09-28 | [Oficial](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=38168) |
| Decreto 24 de 2016 | Función Pública | 4 | 4 | 2026-09-28 | [Oficial](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=67536) |
| Decreto 405 de 2025 | Función Pública | 3 | 3 | 2026-09-28 | [Oficial](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=259517) |
| Decreto 4334 de 2008 | Función Pública | 18 | 18 | 2026-09-28 | [Oficial](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=33747) |
| Decreto 4436 de 2005 | Función Pública | 8 | 8 | 2026-09-28 | [Oficial](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=18346) |
| Decreto 4886 de 2011 | Función Pública | 39 | 39 | 2026-09-28 | [Oficial](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=66371) |
| Decreto 663 de 1993 | Función Pública | 546 | 414 | 2026-09-28 | [Oficial](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=1348) |
| Decreto 780 de 2016 | Función Pública | 2385 | 2364 | 2026-09-28 | [Oficial](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=77813) |
| Decreto 960 de 1970 | Función Pública | 233 | 233 | 2026-09-28 | [Oficial](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=149249) |
| Estatuto del Consumidor (Ley 1480 de 2011) | Función Pública | 92 | 92 | 2026-09-28 | [Oficial](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=44306) |
| Estatuto Tributario (Decreto 624 de 1989) | Función Pública | 1462 | 1450 | 2026-09-28 | [Oficial](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=6533) |
| Ley 1010 de 2006 | Función Pública | 19 | 19 | 2026-09-28 | [Oficial](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=18843) |
| Ley 1095 de 2006 | Función Pública | 10 | 10 | 2026-09-28 | [Oficial](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=22087) |
| Ley 1116 de 2006 | Función Pública | 131 | 131 | 2026-09-28 | [Oficial](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=22657) |
| Ley 1150 de 2007 | Función Pública | 43 | 43 | 2026-09-28 | [Oficial](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=184686) |
| Ley 1151 de 2007 | Función Pública | 232 | 232 | 2026-09-28 | [Oficial](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=25932) |
| Ley 1258 de 2008 | Función Pública | 46 | 46 | 2026-09-28 | [Oficial](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=34130) |
| Ley 1340 de 2009 | Función Pública | 35 | 35 | 2026-09-28 | [Oficial](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=36912) |
| Ley 137 de 1994 | Función Pública | 19 | 19 | 2026-09-28 | [Oficial](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=13966) |
| Ley 1473 de 2011 | Función Pública | 5 | 5 | 2026-09-28 | [Oficial](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=43236) |
| Ley 153 de 1887 | Función Pública | 328 | 326 | 2026-09-28 | [Oficial](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=15805) |
| Ley 155 de 1959 | Función Pública | 23 | 19 | 2026-09-28 | [Oficial](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=38169) |
| Ley 1562 de 2012 | Función Pública | 39 | 39 | 2026-09-28 | [Oficial](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=48365) |
| Ley 1581 de 2012 | Función Pública | 30 | 30 | 2026-09-28 | [Oficial](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=49981) |
| Ley 1607 de 2012 | Función Pública | 287 | 285 | 2026-09-28 | [Oficial](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=51040) |
| Ley 160 de 1994 | Función Pública | 126 | 126 | 2026-09-28 | [Oficial](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=66789) |
| Ley 1700 de 2013 | Función Pública | 13 | 13 | 2026-09-28 | [Oficial](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=56283) |
| Ley 1755 de 2015 | Función Pública | 23 | 23 | 2026-09-28 | [Oficial](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=65334) |
| Ley 1819 de 2016 | Función Pública | 461 | 461 | 2026-09-28 | [Oficial](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=79140) |
| Ley 1909 de 2018 | Función Pública | 32 | 32 | 2026-09-28 | [Oficial](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=87302) |
| Ley 2114 de 2021 | Función Pública | 9 | 9 | 2026-09-28 | [Oficial](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=167967) |
| Ley 2141 de 2021 | Función Pública | 3 | 3 | 2026-09-28 | [Oficial](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=168351) |
| Ley 2157 de 2021 | Función Pública | 7 | 7 | 2026-09-28 | [Oficial](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=173246) |
| Ley 2160 de 2021 | Función Pública | 6 | 6 | 2026-09-28 | [Oficial](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=173787) |
| Ley 2220 de 2022 | Función Pública | 152 | 152 | 2026-09-28 | [Oficial](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=188766) |
| Ley 2251 de 2022 | Función Pública | 24 | 24 | 2026-09-28 | [Oficial](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=189806) |
| Ley 2437 de 2024 | Función Pública | 28 | 28 | 2026-09-28 | [Oficial](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=256656) |
| Ley 2452 de 2025 | Función Pública | 339 | 339 | 2026-09-28 | [Oficial](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=259639) |
| Ley 2466 de 2025 | Función Pública | 74 | 74 | 2026-09-28 | [Oficial](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=260676) |
| Ley 256 de 1996 | Función Pública | 33 | 33 | 2026-09-28 | [Oficial](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=38871) |
| Ley 29 de 1982 | Función Pública | 11 | 11 | 2026-09-28 | [Oficial](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=256) |
| Ley 50 de 1990 | Función Pública | 118 | 118 | 2026-09-28 | [Oficial](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=281) |
| Ley 527 de 1999 | Función Pública | 47 | 47 | 2026-09-28 | [Oficial](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=4276) |
| Ley 54 de 1990 | Función Pública | 8 | 8 | 2026-09-28 | [Oficial](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=30896) |
| Ley 600 de 2000 | Función Pública | 490 | 460 | 2026-09-28 | [Oficial](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=6389) |
| Ley 640 de 2001 | Función Pública | 50 | 50 | 2026-09-28 | [Oficial](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=6059) |
| Ley 678 de 2001 | Función Pública | 32 | 32 | 2026-09-28 | [Oficial](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=4164) |
| Ley 721 de 2001 | Función Pública | 8 | 8 | 2026-09-28 | [Oficial](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=9565) |
| Ley 75 de 1968 | Función Pública | 68 | 68 | 2026-09-28 | [Oficial](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=4828) |
| Ley 769 de 2002 | Función Pública | 194 | 194 | 2026-09-28 | [Oficial](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=5557) |
| Ley 80 de 1993 | Función Pública | 105 | 100 | 2026-09-28 | [Oficial](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=304) |
| Ley 820 de 2003 | Función Pública | 44 | 44 | 2026-09-28 | [Oficial](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=8738) |
| Ley 979 de 2005 | Función Pública | 5 | 5 | 2026-09-28 | [Oficial](https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=30898) |
| Sentencia C-1033 de 2002 | Corte Constitucional | 20 | 20 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2002/C-1033-02.htm) |
| Sentencia C-106 de 2018 | Corte Constitucional | 69 | 69 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2018/C-106-18.htm) |
| Sentencia C-117 de 2018 | Corte Constitucional | 96 | 96 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2018/C-117-18.htm) |
| Sentencia C-1189 de 2000 | Corte Constitucional | 40 | 40 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2000/C-1189-00.htm) |
| Sentencia C-127 de 2011 | Corte Constitucional | 36 | 36 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2011/C-127-11.htm) |
| Sentencia C-131 de 2018 | Corte Constitucional | 36 | 36 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2018/C-131-18.htm) |
| Sentencia C-134 de 2019 | Corte Constitucional | 22 | 22 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2019/C-134-19.htm) |
| Sentencia C-145 de 2018 | Corte Constitucional | 45 | 45 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2018/C-145-18.htm) |
| Sentencia C-145 de 2020 | Corte Constitucional | 157 | 157 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2020/C-145-20.htm) |
| Sentencia C-149 de 1993 | Corte Constitucional | 19 | 19 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/1993/C-149-93.htm) |
| Sentencia C-15 de 2018 | Corte Constitucional | 74 | 74 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2018/C-015-18.htm) |
| Sentencia C-164 de 2022 | Corte Constitucional | 80 | 80 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2022/C-164-22.htm) |
| Sentencia C-170 de 2004 | Corte Constitucional | 53 | 53 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2004/C-170-04.htm) |
| Sentencia C-183 de 2025 | Corte Constitucional | 84 | 84 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2025/C-183-25.htm) |
| Sentencia C-201 de 2002 | Corte Constitucional | 52 | 52 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2002/C-201-02.htm) |
| Sentencia C-207 de 2019 | Corte Constitucional | 152 | 152 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2019/C-207-19.htm) |
| Sentencia C-225 de 1995 | Corte Constitucional | 65 | 65 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/1995/C-225-95.htm) |
| Sentencia C-22 de 1996 | Corte Constitucional | 11 | 11 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/1996/C-022-96.htm) |
| Sentencia C-233 de 2021 | Corte Constitucional | 218 | 218 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2021/C-233-21.htm) |
| Sentencia C-239 de 1997 | Corte Constitucional | 104 | 104 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/1997/C-239-97.htm) |
| Sentencia C-259 de 2015 | Corte Constitucional | 62 | 62 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2015/C-259-15.htm) |
| Sentencia C-276 de 2025 | Corte Constitucional | 67 | 67 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2025/C-276-25.htm) |
| Sentencia C-332 de 2025 | Corte Constitucional | 54 | 54 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2025/C-332-25.htm) |
| Sentencia C-335 de 2008 | Corte Constitucional | 45 | 45 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2008/C-335-08.htm) |
| Sentencia C-345 de 2017 | Corte Constitucional | 59 | 59 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2017/C-345-17.htm) |
| Sentencia C-355 de 2006 | Corte Constitucional | 545 | 545 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2006/C-355-06.htm) |
| Sentencia C-35 de 2009 | Corte Constitucional | 41 | 41 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2009/C-035-09.htm) |
| Sentencia C-389 de 2023 | Corte Constitucional | 43 | 43 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2023/C-389-23.htm) |
| Sentencia C-394 de 2017 | Corte Constitucional | 98 | 98 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2017/C-394-17.htm) |
| Sentencia C-39 de 2025 | Corte Constitucional | 102 | 102 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2025/C-039-25.htm) |
| Sentencia C-413 de 1996 | Corte Constitucional | 10 | 10 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/1996/C-413-96.htm) |
| Sentencia C-431 de 2001 | Corte Constitucional | 8 | 8 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2001/C-431-01.htm) |
| Sentencia C-459 de 2023 | Corte Constitucional | 46 | 46 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2023/C-459-23.htm) |
| Sentencia C-486 de 1993 | Corte Constitucional | 30 | 30 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/1993/C-486-93.htm) |
| Sentencia C-4 de 1998 | Corte Constitucional | 13 | 13 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/1998/C-004-98.htm) |
| Sentencia C-500 de 2024 | Corte Constitucional | 50 | 50 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2024/C-500-24.htm) |
| Sentencia C-507 de 2004 | Corte Constitucional | 133 | 133 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2004/C-507-04.htm) |
| Sentencia C-533 de 2000 | Corte Constitucional | 11 | 11 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2000/C-533-00.htm) |
| Sentencia C-535 de 2002 | Corte Constitucional | 14 | 14 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2002/C-535-02.htm) |
| Sentencia C-537 de 1995 | Corte Constitucional | 28 | 28 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/1995/C-537-95.htm) |
| Sentencia C-540 de 2023 | Corte Constitucional | 53 | 53 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2023/C-540-23.htm) |
| Sentencia C-55 de 2022 | Corte Constitucional | 477 | 477 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2022/C-055-22.htm) |
| Sentencia C-582 de 1999 | Corte Constitucional | 13 | 13 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/1999/C-582-99.htm) |
| Sentencia C-683 de 2015 | Corte Constitucional | 204 | 204 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2015/C-683-15.htm) |
| Sentencia C-700 de 1999 | Corte Constitucional | 110 | 110 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/1999/C-700-99.htm) |
| Sentencia C-746 de 2011 | Corte Constitucional | 17 | 17 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2011/C-746-11.htm) |
| Sentencia C-748 de 2011 | Corte Constitucional | 265 | 265 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2011/C-748-11.htm) |
| Sentencia C-80 de 2025 | Corte Constitucional | 68 | 68 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2025/C-080-25.htm) |
| Sentencia C-891 de 2012 | Corte Constitucional | 28 | 28 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2012/C-891-12.htm) |
| Sentencia C-94 de 2021 | Corte Constitucional | 63 | 63 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2021/C-094-21.htm) |
| Sentencia C-964 de 2003 | Corte Constitucional | 36 | 36 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2003/C-964-03.htm) |
| Sentencia C-96 de 2024 | Corte Constitucional | 84 | 84 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2024/C-096-24.htm) |
| Sentencia C-985 de 2010 | Corte Constitucional | 39 | 39 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2010/C-985-10.htm) |
| Sentencia SL-3385 de 2022 | Corte Suprema de Justicia | 11 | 11 | 2026-09-28 | [Oficial](https://cortesuprema.gov.co/corte/wp-content/uploads/relatorias/la/bnov2022/SL3385-2022.pdf) |
| Sentencia SU-111 de 2025 | Corte Constitucional | 90 | 90 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2025/SU111-25.htm) |
| Sentencia SU-11 de 2020 | Corte Constitucional | 60 | 60 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2020/SU011-20.htm) |
| Sentencia SU-138 de 2024 | Corte Constitucional | 103 | 103 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2024/SU138-24.htm) |
| Sentencia SU-149 de 2021 | Corte Constitucional | 61 | 61 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2021/SU149-21.htm) |
| Sentencia SU-207 de 2022 | Corte Constitucional | 72 | 72 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2022/SU207-22.htm) |
| Sentencia SU-214 de 2016 | Corte Constitucional | 281 | 281 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2016/SU214-16.htm) |
| Sentencia SU-240 de 2015 | Corte Constitucional | 52 | 52 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2015/SU240-15.htm) |
| Sentencia SU-27 de 2021 | Corte Constitucional | 52 | 52 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2021/SU027-21.htm) |
| Sentencia SU-296 de 2023 | Corte Constitucional | 79 | 79 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2023/SU296-23.htm) |
| Sentencia SU-315 de 2025 | Corte Constitucional | 88 | 88 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2025/SU315-25.htm) |
| Sentencia SU-380 de 2021 | Corte Constitucional | 67 | 67 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2021/SU380-21.htm) |
| Sentencia SU-396 de 2024 | Corte Constitucional | 99 | 99 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2024/SU396-24.htm) |
| Sentencia SU-425 de 2025 | Corte Constitucional | 41 | 41 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2025/SU425-25.htm) |
| Sentencia SU-429 de 2024 | Corte Constitucional | 131 | 131 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2024/SU429-24.htm) |
| Sentencia SU-431 de 2015 | Corte Constitucional | 86 | 86 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2015/SU431-15.htm) |
| Sentencia SU-455 de 2020 | Corte Constitucional | 53 | 53 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2020/SU455-20.htm) |
| Sentencia SU-500 de 2015 | Corte Constitucional | 109 | 109 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2015/SU500-15.htm) |
| Sentencia SU-566 de 2015 | Corte Constitucional | 96 | 96 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2015/SU566-15.htm) |
| Sentencia T-1001 de 2001 | Corte Constitucional | 32 | 32 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2001/T-1001-01.htm) |
| Sentencia T-1059 de 2001 | Corte Constitucional | 20 | 20 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2001/T-1059-01.htm) |
| Sentencia T-1096 de 2008 | Corte Constitucional | 33 | 33 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2008/T-1096-08.htm) |
| Sentencia T-145 de 2016 | Corte Constitucional | 41 | 41 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2016/T-145-16.htm) |
| Sentencia T-230 de 2023 | Corte Constitucional | 15 | 15 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2023/T-230-23.htm) |
| Sentencia T-232 de 2025 | Corte Constitucional | 49 | 49 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2025/T-232-25.htm) |
| Sentencia T-243 de 2018 | Corte Constitucional | 38 | 38 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2018/T-243-18.htm) |
| Sentencia T-262 de 2025 | Corte Constitucional | 53 | 53 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2025/T-262-25.htm) |
| Sentencia T-26 de 2025 | Corte Constitucional | 74 | 74 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2025/T-026-25.htm) |
| Sentencia T-323 de 2024 | Corte Constitucional | 138 | 138 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2024/T-323-24.htm) |
| Sentencia T-325 de 2025 | Corte Constitucional | 37 | 37 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2025/T-325-25.htm) |
| Sentencia T-350 de 2025 | Corte Constitucional | 49 | 49 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2025/T-350-25.htm) |
| Sentencia T-429 de 2011 | Corte Constitucional | 22 | 22 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2011/T-429-11.htm) |
| Sentencia T-445 de 2024 | Corte Constitucional | 71 | 71 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2024/T-445-24.htm) |
| Sentencia T-4 de 2026 | Corte Constitucional | 54 | 54 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2026/T-004-26.htm) |
| Sentencia T-547 de 2017 | Corte Constitucional | 38 | 38 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2017/T-547-17.htm) |
| Sentencia T-67 de 2025 | Corte Constitucional | 100 | 100 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2025/T-067-25.htm) |
| Sentencia T-71 de 2016 | Corte Constitucional | 47 | 47 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2016/T-071-16.htm) |
| Sentencia T-760 de 2008 | Corte Constitucional | 464 | 464 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2008/T-760-08.htm) |
| Sentencia T-77 de 2025 | Corte Constitucional | 40 | 40 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2025/T-077-25.htm) |
| Sentencia T-925 de 2014 | Corte Constitucional | 20 | 20 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2014/T-925-14.htm) |
| Sentencia T-970 de 2014 | Corte Constitucional | 56 | 56 | 2026-09-28 | [Oficial](https://www.corteconstitucional.gov.co/relatoria/2014/T-970-14.htm) |

## Objetivos pendientes

Los errores detallados se conservan en el manifest y en `corpus/acquisition.json`. Una coincidencia aproximada en año o número no se acepta como la misma norma.

- `acuerdo_02_de_2015` — download.
- `decreto_046_de_2024` — download.
- `decreto_1563_de_2012` — download.
- `decreto_875_de_2008` — download.
- `ley_11500_de_2007` — download.
- `ley_1150_de_2005` — download.
- `ley_116_de_2006` — download.
- `ley_1692_de_2017` — download.
- `ley_23_de_1961` — download.
- `ley_2737_de_1989` — download.
- `ley_964_de_2006` — download.
- `sentencia_sc_1121_de_2018` — download.
- `sentencia_sc_18392_de_2017` — download.
- `sentencia_sc_3085_de_2024` — download.
- `sentencia_sc_3674_de_2021` — download.
- `sentencia_sc_425_de_2024` — download.
- `sentencia_sc_8453_de_2016` — download.
- `sentencia_sl_1050_de_2023` — download.
- `sentencia_sl_1730_de_2020` — download.
- `sentencia_sl_1972_de_2025` — download.
- `sentencia_sl_648_de_2018` — download.
- `sentencia_sp_1167_de_2022` — download.
- `sentencia_sp_1680_de_2022` — download.
- `sentencia_sp_1945_de_2019` — download.
- `sentencia_sp_3218_de_2021` — download.
- `sentencia_su_488_de_2011` — download.
- `sentencia_su_6_de_1991` — download.
- `sentencia_t_248_de_2025` — download.

## Ambigüedades excluidas

| Documento | Numeraciones repetidas | Pasajes afectados |
|---|---:|---:|
| `codigo_comercio` | 6 | 12 |
| `codigo_procedimiento_penal` | 1 | 7 |
| `constitucion` | 27 | 67 |
| `decreto_1082_de_2015` | 19 | 38 |
| `decreto_2153_de_1992` | 1 | 2 |
| `decreto_780_de_2016` | 10 | 21 |
| `estatuto_tributario` | 6 | 12 |
| `ley_153_de_1887` | 1 | 2 |
| `ley_155_de_1959` | 1 | 3 |
| `ley_1607_de_2012` | 1 | 2 |
| `ley_600_de_2000` | 15 | 30 |


## Benchmark interno de retrieval v1

Sobre este mismo snapshot se creó `benchmarks/kingscode_ir/`: 200 casos
source-derived, gold IDs/spans canónicos verificables y 120/40/40 dev/validation/holdout.
No altera el corpus ni lo usa como proxy de calidad. R0 BM25 y los diagnósticos
CPU están en `reports/benchmark/`; Qwen/BGE/hybrid/reranker siguen bloqueados
por GPU/configuración. El reporte de selección declara honestamente
`no_selection` hasta medir las variantes R1–R8 correctas sobre la 4090.

## Snapshot histórico y transición v0.2 (2026-09-28)

Corpus-v0.1 (163 documentos, 26,558 pasajes, 26,060 indexables) queda inmutable como base medida de RTX4090/Search V2. Hashes de pasajes/grafo/BM25 contrastados con `reports/gpu_freeze_4090/CRITICAL_ARTIFACT_HASHES.json`; ver `reports/member_a_v02/gpu_reconciliation.json`. Dense histórico: `0c156c5e95dce92d6abd6404a39242bd724228bfdf99f4e9e44ddf5dd16b8347` (registro del entorno GPU; bytes no disponibles en este checkout CPU). No se infiere vigencia ni calidad total del parser de estos hashes.

Toda nueva fuente, parsing corregido, grafo o BM25 pertenece a `corpora/corpus-v0.2/`. La prioridad es revisar los 28 targets originales, cerrar brechas CSJ/Consejo de Estado y resolver nodos externos con evidencia oficial. El plan distingue fuente localizada, texto adquirido y documento aceptado. No se construye dense v0.2 durante esta sesión.

## Candidato separado corpus-v0.3 (2026-10-03)

`corpora/corpus-v03-additions/` conserva tres sentencias oficiales de unificación del Consejo de Estado, preseleccionadas antes de su descarga en `docs/CORPUS_V03_ACQUISITION_PLAN.md`. El candidato combinado `corpus_v03_candidate/` es diagnóstico y no modifica este snapshot histórico.

| Fuente oficial | Motivo de cobertura | SHA-256 del PDF |
|---|---|---|
| [SUJ-032-CE-S2-2023, Sección Segunda](https://www.consejodeestado.gov.co/wp-content/uploads/2023/113_660013333001202200016011SENTENCIA2023101119112_231012_124317%20%281%29.pdf) | Empleo público, cesantías, prescripción y reclamación administrativa; cubre la sección laboral pública. | `9038a2e16b477b283ab61c296569b46bc583996f74f5892eee13c8597e89e8c0` |
| [Unificación 24897, Sección Tercera](https://consejodeestado.gov.co/documentos/boletines/115/S3/73001-23-31-000-2000-03075-01%2824897%29.pdf) | Actio in rem verso / enriquecimiento sin causa y procedencia procesal contencioso-administrativa. | `0a505e152dcf7a5c37183b1126fc26bfbbd1214b930145ee7109e40aa05a329c` |
| [2022CE-SUJ-4-002, Sección Cuarta](https://consejodeestado.gov.co/wp-content/uploads/2022/UnifImp.pdf) | Corrección tributaria, imputaciones y término del artículo 43 de la Ley 962/2005. | `c9f5acf699f0a97f7b602daa9ef3e6f1d7c284fe8f756e32fb82e27d7eb26e7f` |

El add-on tiene 3 documentos, 162 pasajes indexables, 69 nodos y 247 aristas. El candidato completo tiene 175 documentos, 27.164 pasajes (26.666 indexables, 498 excluidos) y conserva los 163 documentos/pasajes de v0.1 como prefijo byte a byte. La cobertura del Consejo de Estado pasa de 0 a 3 decisiones; administrativo pasa de 16 a 22 documentos (3.484 a 3.825 pasajes indexables), procesal de 10 a 13 (2.438 a 2.600), y tributario de 18 a 19 (4.139 a 4.151).

Fingerprints del candidato combinado: passages `69e60632dc22c51e218d45cbc90cf52f2b55c71367c597768f5b0aff6a00c030`; grafo/nodos `0205c7ee6d85af869ad40cb60940757472d2f250dd5dad90b2747527f8ecf0fc`; grafo/aristas `ad80a17039fecc9b8ecc107d812df082ab2101b5585c46c06547bbf03ba80f7b`; BM25 `547c2de1568d72e0b7fdbd44bdc24320c4cf69efde37e83b0c7a224b991edaf0`. El fingerprint path-independiente del conjunto runtime es `019b7b3a2c6e719cd70dd082ef61e63042f1dee3113b551f1028bcd14b964b91`.

No es un freeze competitivo. La prueba BM25 C0/C1 del benchmark interno Member-A y la puerta sample_50 en RTX 4090 se registran por separado; no hay resultado GPU de este candidato en este host.

## Resultado independiente C0/C1 (2026-10-03)

R0/BM25 se ejecutó en las mismas 120 preguntas DEV, commit `65f4fe133d6a28c8463a7689dad7b1c3dfc0aa91`, mismo benchmark (manifest SHA `326a405748dd20f641d5cf4103ceaafb6a19f07b43db54d95f472a2b439e3071`). C0 usó v0.1; C1 usó el candidato append-only, con prefijo de v0.1 validado byte a byte. C0→C1: Recall@1 0,163→0,163; @3 0,300→0,296; @5 0,438→0,446; @8 0,604→0,592; @10 0,650→0,667; MRR@10 0,3065→0,3061; nDCG@10 0,3859→0,3894; Evidence Completeness@8 0,533→0,517; Document Recall@10 1,000→1,000; mismatch 0,025→0,025; latencia p50 65,3→64,9 ms y p95 86,3→80,7 ms.

Bootstrap pareado (10.000 remuestras, seed 0): EC@8 delta −0,0167, IC95 [−0,0417; 0,0000]; Recall@10 +0,0167, IC95 [0,0000; 0,0417]; MRR@10 −0,00036, IC95 [−0,00447; 0,00340]. Ninguna zona objetivo (administrativo, procesal, tributario) tuvo mejora positiva demostrada. Gate `NOT_PASSED`; no se corre sample_50. El benchmark v1 no contiene gold jurisprudencial ni Consejo de Estado: estas métricas no prueban ni refutan la relevancia de las tres nuevas sentencias. El corpus candidato queda diagnóstico y no se declara ganador. Informe pareado: `reports/benchmark/corpus_v03_c1/paired_comparison.json`; decisión/gate: `reports/corpus_v03_independent_retrieval_comparison.json`; desglose descriptivo: `reports/corpus_v03_source_breakdown.md`.
