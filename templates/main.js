const cityInput = document.getElementById('cityInput');
const statusDiv = document.getElementById('status');
const resultsDiv = document.getElementById('results');
const zoneReportPre = document.getElementById('zoneReport');
const sourcesReportPre = document.getElementById('sourcesReport');
const startButton = document.getElementById('startButton');

async function startAnalysis() {
    const city = cityInput.value;
    if (!city) {
        alert('請輸入城市名稱！');
        return;
    }

    startButton.disabled = true;
    statusDiv.textContent = '處理中，請稍候... 由於需要執行複雜的分析，這可能會花費數分鐘時間，請不要關閉此頁面。';
    statusDiv.style.color = 'blue';
    resultsDiv.style.display = 'none';

    try {
        const response = await fetch('/api/run-analysis', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ city: city }),
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: '發生未知伺服器錯誤' }));
            throw new Error(errorData.detail);
        }

        const data = await response.json();

        statusDiv.textContent = '分析完成！';
        statusDiv.style.color = 'green';
        resultsDiv.style.display = 'block';
        zoneReportPre.textContent = data.zone_report;
        sourcesReportPre.textContent = data.sources_report;

    } catch (error) {
        statusDiv.textContent = `錯誤: ${error.message}`;
        statusDiv.style.color = 'red';
    } finally {
        startButton.disabled = false;
    }
}
