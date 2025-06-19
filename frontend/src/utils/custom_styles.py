style_sheet = """
<style>

[data-testid="stAppViewContainer"] {
    background-color: #f0f0f0;
}

[data-testid="stFullScreenFrame"] {
    background-color: white;
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1); 
}

[data-testid="stHeader"] {
    background-color: #6c5ce7;
    color: white;
}

[data-testid="stMetric"] {
    background-color: white; 
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
    text-align: center;
    padding: 15px 10px; 
}

[data-testid="stMetricLabel"] {
    font-weight: bold;
    margin-bottom: 10px;
    display: flex; 
    position: relative; 
}

[data-testid="stMetricLabel"] p {
    font-size: 15pt !important;
    font-weight: bold; 
    text-transform: uppercase
}

[data-testid="stMetricValue"] {
    font-size: 25px;
}

[data-testid="stMetricLabel"]::after {
    content: "";
    position: absolute; 
    bottom: -5px; 
    width: 100%;
    height: 2.5px;
    background-color: #6c5ce7; 
}

[data-testid="stTable"] {
    padding-top: 0.5px;
    padding-right: 0.5px;
    height: 458px !important;
    width: 100%;
}

[data-testid="stTable"] tr{
    font-size: 15px;
}

th {
        text-transform: uppercase !important;
        text-align: center !important;
        padding: 15px 10px !important;
        border: 1px solid #ddd !important;
        background-color: #6c5ce7 !important;
        color: white !important;
        font-weight: bold !important;
      }
      
[data-testid="stTable"] th{
    text-transform: uppercase;
    text-align: center !important;
    padding: 15px 10px;
    border: 1px solid #ddd;
    background-color: #6c5ce7;
    color: white;
    font-weight: bold;
}

[data-testid="stTable"] td {
    padding: 10px 10px;
}

[data-testid="stTable"] tr:nth-child(even) {
    background-color: #f2f2f5;
}

[data-testid="stTable"] tr:hover {
    background-color: #ddd;
}

[data-testid="stImage"]{
    height: 450px !important;
}

[data-testid="stImage"] > figure img {
    max-width: 100% !important;
    max-height: 450px !important;
    object-fit: fit;
}

[data-testid="stTableStyledEmptyTableCell"] {
    font-size: 0;
}

[data-testid="stTableStyledEmptyTableCell"]::before {
    content: "Nothing to show yet! Mininig Data-Aware DECLARE Models ...";
    font-size: 16px;
}

.block-container {
    padding-top: 30pt !important;
    padding-bottom: 20pt !important;
}
</style>
"""