const cityInput = document.getElementById('cityInput');
const statusDiv = document.getElementById('status');
const resultsDiv = document.getElementById('results');
const zoneReportPre = document.getElementById('zoneReport');
const sourcesReportPre = document.getElementById('sourcesReport');
const startButton = document.getElementById('startButton');

async function startAnalysis() {
    const city = cityInput.value;
    if (!city) {
        alert('都市名を入力してください！');
        return;
    }

    startButton.disabled = true;
    statusDiv.textContent = '処理中です。しばらくお待ちください... 複雑な分析を実行するため、数分かかる場合があります。このページを閉じないでください。';
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
            const errorData = await response.json().catch(() => ({ detail: '不明なサーバーエラーが発生しました' }));
            throw new Error(errorData.detail);
        }

        const data = await response.json();

        statusDiv.textContent = '分析完了！';
        statusDiv.style.color = 'green';
        resultsDiv.style.display = 'block';
        zoneReportPre.textContent = data.zone_report;
        sourcesReportPre.textContent = data.sources_report;

    } catch (error) {
        statusDiv.textContent = `エラー: ${error.message}`;
        statusDiv.style.color = 'red';
    } finally {
        startButton.disabled = false;
    }
}
