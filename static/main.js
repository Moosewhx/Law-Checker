const cityInput = document.getElementById('cityInput');
const statusDiv = document.getElementById('status');
const resultsDiv = document.getElementById('results');
const reportDiv = document.getElementById('report');
const linksDiv = document.getElementById('links');
const pdfsDiv = document.getElementById('pdfs');
const startButton = document.getElementById('startButton');

async function startAnalysis() {
    const city = cityInput.value.trim();
    if (!city) {
        alert('都市名を入力してください！');
        return;
    }

    startButton.disabled = true;
    statusDiv.textContent = '処理中です。関連リンクを検索・フィルタリングしています... 数分かかる場合があります。';
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

        statusDiv.textContent = `分析完了！${data.summary}`;
        statusDiv.style.color = 'green';
        resultsDiv.style.display = 'block';
        
        // 显示报告
        reportDiv.innerHTML = markdownToHtml(data.report);
        
        // 显示相关链接
        if (data.relevant_links && data.relevant_links.length > 0) {
            let linksHtml = '<h3>関連性の高いリンク</h3><ul>';
            data.relevant_links.forEach((link, index) => {
                linksHtml += `<li>
                    <strong>${link.type}</strong>: 
                    <a href="${link.url}" target="_blank" rel="noopener">${link.url}</a>
                    ${link.downloaded ? ` <span style="color: green;">[ダウンロード済み]</span>` : ''}
                </li>`;
            });
            linksHtml += '</ul>';
            linksDiv.innerHTML = linksHtml;
        } else {
            linksDiv.innerHTML = '<h3>関連リンクが見つかりませんでした</h3>';
        }
        
        // 显示PDF下载链接
        if (data.pdf_downloads && data.pdf_downloads.length > 0) {
            let pdfsHtml = '<h3>ダウンロード済みPDFファイル</h3><ul>';
            data.pdf_downloads.forEach(pdf => {
                pdfsHtml += `<li>
                    <a href="${pdf.local_path}" target="_blank">${pdf.filename}</a>
                    <small> (元URL: <a href="${pdf.original_url}" target="_blank" rel="noopener">リンク</a>)</small>
                </li>`;
            });
            pdfsHtml += '</ul>';
            pdfsDiv.innerHTML = pdfsHtml;
        } else {
            pdfsDiv.innerHTML = '<h3>ダウンロードできたPDFファイルはありませんでした</h3>';
        }

    } catch (error) {
        statusDiv.textContent = `エラー: ${error.message}`;
        statusDiv.style.color = 'red';
    } finally {
        startButton.disabled = false;
    }
}

function markdownToHtml(markdown) {
    return markdown
        .replace(/^### (.+)$/gm, '<h4>$1</h4>')
        .replace(/^## (.+)$/gm, '<h3>$1</h3>')
        .replace(/^# (.+)$/gm, '<h2>$1</h2>')
        .replace(/^- (.+)$/gm, '<li>$1</li>')
        .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>')
        .replace(/\n/g, '<br>');
}
