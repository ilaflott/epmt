To reproduce this example, you will need the following test data:

```
$ epmt submit test/data/outliers_nb/*.tgz
```

You run the CLI by typing `epmt explore` and passing it an
experiment name:

```
$ epmt explore ESM4_hist-piAer_D1

top 10 components by sum(duration):
       component           sum                  min          max   cv
      atmos_cmip: 724269037393 [27.9%]  18341471496 204199142602  1.0
    aerosol_cmip: 231354197391 [ 8.9%]  10153792721 190797258254  1.3
    tracer_level: 221748381029 [ 8.5%]   7790096988 186490389153  1.4
       land_cmip: 221357047122 [ 8.5%]   6767103209 188810565604  1.4
           atmos: 213604322234 [ 8.2%]   5939740040 184454576055  1.4
     atmos_level: 213582094835 [ 8.2%]   5792509494 185460453836  1.4
       land_dust: 212434109350 [ 8.2%]   5072225424 185102124432  1.4
           river: 208332928054 [ 8.0%]   5324197745 185639226822  1.5
ocean_inert_mont: 186783450315 [ 7.2%]   5657762994 161584773372  1.4
ocean_cobalt_flu: 164048147551 [ 6.3%]   4765560367 140959995935  1.4

variations across time segments (by component):
       component     exp_time        jobid         duration
      atmos_cmip     18540101      2444931      32855829382       
      atmos_cmip     18590101      2460340     204199142602 ******
      atmos_cmip     18640101      2494089      29236399996       
      atmos_cmip     18690101      2501763      23686775771       
      atmos_cmip     18740101      2546910      23599609407       
      atmos_cmip     18790101      2549352      28351433443       
      atmos_cmip     18840101      2557075      37029135366       
      atmos_cmip     18890101      2568088      32242271376       
      atmos_cmip     18940101      2577413      22275760224       
      atmos_cmip     18990101      2579660      22412951465       
      atmos_cmip     19040101      2581160      27724830811       
      atmos_cmip     19090101      2587725      34461532496       
      atmos_cmip     19140101      2600696      23704338393       
      atmos_cmip     19190101      2605559      18341471496       
      atmos_cmip     19240101      2621360      36262018973       
      atmos_cmip     19290101      2626358      21122417938       
      atmos_cmip     19340101      2628013      44092005094       
      atmos_cmip     19390101      2632680      23934831859       
      atmos_cmip     19440101      2641421      38736281301       

    aerosol_cmip     18540101      2444929      18941050858       
    aerosol_cmip     18590101      2460338     190797258254   ****
    aerosol_cmip     18640101      2494087      11462095558       
    aerosol_cmip     18690101      2501761      10153792721       

    tracer_level     18540101      2444963      18595376229       
    tracer_level     18590101      2460367     186490389153   ****
    tracer_level     18640101      2494114       8872518659       
    tracer_level     18690101      2501788       7790096988       

       land_cmip     18540101      2444941      18092808472       
       land_cmip     18590101      2460345     188810565604   ****
       land_cmip     18640101      2494093       7686569837       
       land_cmip     18690101      2501767       6767103209       

           atmos     18540101      2444930      17183979158       
           atmos     18590101      2460339     184454576055   ****
           atmos     18640101      2494088       6026026981       
           atmos     18690101      2501762       5939740040       

     atmos_level     18540101      2444933      16371862622       
     atmos_level     18590101      2460342     185460453836   ****
     atmos_level     18640101      2494091       5957268883       
     atmos_level     18690101      2501765       5792509494       

       land_dust     18540101      2444942      17169830899       
       land_dust     18590101      2460346     185102124432   ****
       land_dust     18640101      2494094       5072225424       
       land_dust     18690101      2501768       5089928595       

           river     18540101      2444962      12039197179       
           river     18590101      2460366     185639226822   ****
           river     18640101      2494113       5330306308       
           river     18690101      2501787       5324197745       

ocean_inert_mont     18540101      2444957      13546647739       
ocean_inert_mont     18590101      2460361     161584773372   ****
ocean_inert_mont     18640101      2494108       5994266210       
ocean_inert_mont     18690101      2501782       5657762994       

ocean_cobalt_flu     18540101      2444948      13399811775       
ocean_cobalt_flu     18590101      2460353     140959995935   ****
ocean_cobalt_flu     18640101      2494100       4765560367       
ocean_cobalt_flu     18690101      2501774       4922779474       

duration by time segment:
    18540101     393276509145   ****
    18590101    3304180657173 ******
    18640101     172377480977   ****
    18690101     162823839955   ****
    18740101      23599609407       
    18790101      28351433443       
    18840101      37029135366       
    18890101      32242271376       
    18940101      22275760224       
    18990101      22412951465       
    19040101      27724830811       
    19090101      34461532496       
    19140101      23704338393       
    19190101      18341471496       
    19240101      36262018973       
    19290101      21122417938       
    19340101      44092005094       
    19390101      23934831859       
    19440101      38736281301       
```

The output is self-explanatory. The outliers are marked with asterisks,
the more the asterisks the greater the outlier. We use multimode score
using a number of univariate classifiers. 

You will notice that the first four time-segments take a bulk of the time.
That's an artifact of the fact that we loaded all the jobs of the first
four time-segments, but only one job each from the remaining segments. So for
now you can safely ignore the variation across time-segments.

In the example above we use the default metric -- `duration`. It shows quite clearly
that the time-segment `18590101` is affected and took far longer.
The output with `cpu_time` metric is also instructive. Have a look:

```
$ epmt explore --metric cpu_time ESM4_hist-piAer_D1

top 10 components by sum(cpu_time):
       component           sum                  min          max   cv
      atmos_cmip: 281553223296 [78.2%]   8919433292  16487905141  0.1
    aerosol_cmip:  18618881029 [ 5.2%]   3969568491   4905402152  0.1
    tracer_level:  13582002508 [ 3.8%]   2570281911   4111950015  0.2
       land_cmip:   8118790419 [ 2.3%]   1742520351   2425312535  0.1
           atmos:   8063244053 [ 2.2%]   1089856333   3661044281  0.5
ocean_inert_mont:   7917665546 [ 2.2%]   1647569929   2492882916  0.2
     atmos_level:   7157903022 [ 2.0%]   1306630387   2944876599  0.4
ocean_monthly_z_:   6899290003 [ 1.9%]   1491928295   2025721148  0.1
ocean_inert_z_1x:   4023442544 [ 1.1%]    781808967   1423019293  0.2
ocean_cobalt_sfc:   3923077492 [ 1.1%]    752897613   1467064093  0.3

variations across time segments (by component):
       component     exp_time        jobid         cpu_time
      atmos_cmip     18540101      2444931      14993597755       
      atmos_cmip     18590101      2460340      13890098079       
      atmos_cmip     18640101      2494089      16052970720       
      atmos_cmip     18690101      2501763      15975897095       
      atmos_cmip     18740101      2546910      13649230447       
      atmos_cmip     18790101      2549352      16487905141       
      atmos_cmip     18840101      2557075      15596840708       
      atmos_cmip     18890101      2568088      15743465184       
      atmos_cmip     18940101      2577413      13673816354       
      atmos_cmip     18990101      2579660      12791008357     **
      atmos_cmip     19040101      2581160      15499418067       
      atmos_cmip     19090101      2587725      15835042318       
      atmos_cmip     19140101      2600696      15738915254       
      atmos_cmip     19190101      2605559       8919433292 ******
      atmos_cmip     19240101      2621360      15412867040       
      atmos_cmip     19290101      2626358      13561761036       
      atmos_cmip     19340101      2628013      16479797891       
      atmos_cmip     19390101      2632680      15447854905       
      atmos_cmip     19440101      2641421      15803303653       

    aerosol_cmip     18540101      2444929       4863690779       
    aerosol_cmip     18590101      2460338       3969568491   ****
    aerosol_cmip     18640101      2494087       4880219607       
    aerosol_cmip     18690101      2501761       4905402152       

    tracer_level     18540101      2444963       3688332827       
    tracer_level     18590101      2460367       2570281911       
    tracer_level     18640101      2494114       4111950015       
    tracer_level     18690101      2501788       3211437755       

       land_cmip     18540101      2444941       2157993314       
       land_cmip     18590101      2460345       1742520351       
       land_cmip     18640101      2494093       1792964219       
       land_cmip     18690101      2501767       2425312535       

           atmos     18540101      2444930       3661044281   ****
           atmos     18590101      2460339       1089856333       
           atmos     18640101      2494088       1492104066       
           atmos     18690101      2501762       1820239373       

ocean_inert_mont     18540101      2444957       2492882916       
ocean_inert_mont     18590101      2460361       1647569929       
ocean_inert_mont     18640101      2494108       2022159153       
ocean_inert_mont     18690101      2501782       1755053548       

     atmos_level     18540101      2444933       2944876599   ****
     atmos_level     18590101      2460342       1562819504       
     atmos_level     18640101      2494091       1343576532       
     atmos_level     18690101      2501765       1306630387       

ocean_monthly_z_     18540101      2444960       2025721148     **
ocean_monthly_z_     18590101      2460364       1491928295       
ocean_monthly_z_     18640101      2494111       1701526557       
ocean_monthly_z_     18690101      2501785       1680114003       

ocean_inert_z_1x     18540101      2444958       1423019293   ****
ocean_inert_z_1x     18590101      2460362        955923522       
ocean_inert_z_1x     18640101      2494109        862690762       
ocean_inert_z_1x     18690101      2501783        781808967       

ocean_cobalt_sfc     18540101      2444955       1467064093   ****
ocean_cobalt_sfc     18590101      2460359        865991754       
ocean_cobalt_sfc     18640101      2494106        837124032       
ocean_cobalt_sfc     18690101      2501780        752897613       

cpu_time by time segment:
    18540101      59029778268   ****
    18590101      37829988097   ****
    18640101      42417908738   ****
    18690101      42561932066   ****
    18740101      13649230447       
    18790101      16487905141       
    18840101      15596840708       
    18890101      15743465184       
    18940101      13673816354       
    18990101      12791008357       
    19040101      15499418067       
    19090101      15835042318       
    19140101      15738915254       
    19190101       8919433292   ****
    19240101      15412867040       
    19290101      13561761036       
    19340101      16479797891       
    19390101      15447854905       
    19440101      15803303653       
```

The `cpu_time` data suggests that the `18590101` took less cpu cycles. Yet it took longer to finish. One hypothesis that could explain the seeming contradiction is if the node(s) where the `18590101` were time-sharing with other concurrently running jobs.


