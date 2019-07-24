   function grafica1( cantidades, nombres, anio, opcion,url) {

    // configure for module loader
        require.config({
            paths: {
                echarts: url + 'static/echarts'
            }
        });

        require(
            [
                'echarts',
                'echarts/chart/bar' // require the specific chart type
            ],
            function (ec) {
                // Initialize after dom ready
                var myChart = ec.init(document.getElementById('main1')); 
                
                option = {
    title : {
        text: opcion + ' con mayor cantidad  de Adjudicaciones en el año '  + anio ,
        subtext: anio 
    },
    tooltip : {
        trigger: 'axis'
    },
   
    toolbox: {
        show : true,
        feature : {
            mark : {show: false},
            dataView : {show: false, readOnly: false},
            magicType: {show: false, type: ['line', 'bar']},
            restore : {show: true},
            saveAsImage : {show: true}
        }
    },
    calculable : true,
    xAxis : [
        {
            type : 'value',
            boundaryGap : [0, 0.09]
        }
    ],
    yAxis : [
        {
            type : 'category',
            data : nombres,
            position: "left",
             axisLabel : {
                show:true,
                interval: 'auto',    // {number}
                rotate: 0,
                margin: -10,
                interval:0,
                clickable: true,
                formatter: '{value}',    // Template formatter!
                textStyle: {
                    color: 'black',
                    align: 'left',
                    
                    fontSize: 14,
                    fontStyle: 'normal',
                    
                }
            }
            
        },

    ],
    series : [
        {
            name:'Cantidad Total de Adjudicaciones',
            type:'bar',
            data: cantidades
        },
        
    ]
};
                                                     
        
                // Load data into the ECharts instance 
                myChart.setOption(option); 
            }
        );


}