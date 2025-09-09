const cityInput = document.getElementById('cityInput');
const statusDiv = document.getElementById('status');
const resultsDiv = document.getElementById('results');
const reportDiv = document.getElementById('report');
const linksDiv = document.getElementById('links');
const pdfsDiv = document.getElementById('pdfs');
const startButton = document.getElementById('startButton');
const toggleDetailsBtn = document.getElementById('toggleDetailsBtn');
const summaryDiv = document.getElementById('summary');

// Modal elements for compact UI
const detailsModal = document.getElementById('detailsModal');
const modalClose = document.getElementById('modalClose');
const modalLinks = document.getElementById('modalLinks');
const modalPdfs = document.getElementById('modalPdfs');
const modalStats = document.getElementById('modalStats');

// Hide legacy sections; we will use a modal for details
const reportSection = reportDiv ? reportDiv.closest('.section') : null;
const linksSection = linksDiv ? linksDiv.closest('.section') : null;
const pdfsSection = pdfsDiv ? pdfsDiv.closest('.section') : null;
if (reportSection) { reportSection.style.display = 'none'; }
if (linksSection) { linksSection.style.display = 'none'; }
if (pdfsSection) { pdfsSection.style.display = 'none'; }

function openModal(){
    if (!detailsModal) return;
    detailsModal.classList.add('show');
    detailsModal.setAttribute('aria-hidden','false');
}
function closeModal(){
    if (!detailsModal) return;
    detailsModal.classList.remove('show');
    detailsModal.setAttribute('aria-hidden','true');
}
if (toggleDetailsBtn){
    toggleDetailsBtn.addEventListener('click', openModal);
}
if (modalClose){
    modalClose.addEventListener('click', closeModal);
}
if (detailsModal){
    detailsModal.addEventListener('click', (e)=>{
        if (e.target.classList.contains('modal-backdrop')) closeModal();
    });
    detailsModal.addEventListener('click', (e)=>{
        const btn = e.target.closest('.accordion-toggle');
        if (!btn) return;
        const sel = btn.getAttribute('data-target');
        const panel = detailsModal.querySelector(sel);
        if (panel) panel.classList.toggle('show');
    });
}

async function startAnalysis() {
    const city = cityInput.value.trim();
    if (!city) {
        alert('都市名を入力してください！');
        return;
    }

    startButton.disabled = true;
    statusDiv.textContent = '処理中です。関連リンクを検索・フィルタリングしています... 10-15分かかる場合があります。ページを閉じないでください。';
    statusDiv.style.color = 'blue';
    resultsDiv.style.display = 'none';
    // Ensure legacy sections stay hidden; reset summary and modal content
    if (reportSection) reportSection.style.display = 'none';
    if (linksSection) linksSection.style.display = 'none';
    if (pdfsSection) pdfsSection.style.display = 'none';
    if (summaryDiv) { summaryDiv.style.display = 'none'; summaryDiv.innerHTML = ''; }
    if (toggleDetailsBtn) toggleDetailsBtn.disabled = true;

    // 创建一个AbortController来处理超时 - 延长到18分钟
    const controller = new AbortController();
    const timeoutId = setTimeout(() => {
        controller.abort();
    }, 1080000); // 18分钟超时 (1080秒)

    try {
        const response = await fetch('/api/run-analysis', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ city: city }),
            signal: controller.signal  // 添加超时信号
        });

        clearTimeout(timeoutId); // 清除超时定时器

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ 
                detail: `サーバーエラー (HTTP ${response.status}): ${response.statusText}` 
            }));
            throw new Error(errorData.detail);
        }

        const data = await response.json();

        // 检查返回的数据结构
        if (!data || typeof data !== 'object') {
            throw new Error('サーバーから無効なデータが返されました');
        }

        statusDiv.textContent = `分析完了！${data.summary || '処理が完了しました'}`;
        statusDiv.style.color = 'green';
        resultsDiv.style.display = 'block';
        if (toggleDetailsBtn) toggleDetailsBtn.disabled = false;
        // Fill modal: relevant links
        if (data.relevant_links && data.relevant_links.length > 0) {
            let linksHtml = '<ul>';
            data.relevant_links.forEach((link) => {
                linksHtml += `<li><strong>${link.type || 'UNKNOWN'}</strong>: <a href="${link.url}" target="_blank" rel="noopener">${link.url}</a>${link.downloaded ? ' <span style="color: green;">[ダウンロード済み]</span>' : ''}</li>`;
            });
            linksHtml += '</ul>';
            if (modalLinks) modalLinks.innerHTML = linksHtml;
        } else {
            if (modalLinks) modalLinks.innerHTML = '<p>関連リンクが見つかりませんでした。</p>';
        }
        // Fill modal: PDFs
        if (data.pdf_downloads && data.pdf_downloads.length > 0) {
            let pdfsHtml = '<ul>';
            data.pdf_downloads.forEach(pdf => {
                pdfsHtml += `<li><a href="${pdf.local_path}" target="_blank">${pdf.filename}</a><small> (元URL: <a href="${pdf.original_url}" target="_blank" rel="noopener">リンク</a>)</small></li>`;
            });
            pdfsHtml += '</ul>';
            if (modalPdfs) modalPdfs.innerHTML = pdfsHtml;
        } else {
            if (modalPdfs) modalPdfs.innerHTML = '<p>ダウンロードできたPDFはありませんでした。</p>';
        }
        // Stats: compact on main, detailed in modal
        if (data.statistics) {
            const s = data.statistics;
            if (summaryDiv) {
                summaryDiv.style.display = 'block';
                summaryDiv.textContent = `総クロール数: ${s.total_crawled || 0}件 ｜ 処理対象数: ${s.processed_count || 0}件 ｜ 関連リンク: ${s.relevant_count || 0}件 ｜ PDF: ${s.pdf_count || 0}件`;
            }
            if (modalStats) {
                modalStats.innerHTML = `<ul><li>総クロール数: ${s.total_crawled || 0}件</li><li>処理対象数: ${s.processed_count || 0}件</li><li>関連リンク数: ${s.relevant_count || 0}件</li><li>PDF数: ${s.pdf_count || 0}件</li></ul>`;
            }
        }

    } catch (error) {
        clearTimeout(timeoutId);
        
        let errorMessage = 'エラーが発生しました';
        
        if (error.name === 'AbortError') {
            errorMessage = 'タイムアウト: 処理に時間がかかりすぎました（18分超過）。サーバーが高負荷の可能性があります。';
        } else if (error.message) {
            errorMessage = `エラー: ${error.message}`;
        }
        
        statusDiv.textContent = errorMessage;
        statusDiv.style.color = 'red';
        
        // Show error inside modal for concise UI
        resultsDiv.style.display = 'block';
        if (modalLinks) modalLinks.innerHTML = `
            <div style="background-color: #ffe6e6; padding: 1em; border-radius: 4px;">
                <h3>エラー</h3>
                <p>${errorMessage}</p>
                <h4>対処方法:</h4>
                <ul>
                    <li>ページを再読み込みして再試行してください</li>
                    <li>別の都市名で試してみてください</li>
                    <li>時間を置いてから再度お試しください</li>
                    <li>問題が続く場合は、開発者コンソール（F12）でエラーを確認してください</li>
                </ul>
            </div>
        `;
        if (modalPdfs) modalPdfs.innerHTML = '';
        if (toggleDetailsBtn) toggleDetailsBtn.disabled = false;
        openModal();
        
        console.error('Analysis error:', error);
    } finally {
        startButton.disabled = false;
    }
}

function markdownToHtml(markdown) {
    if (!markdown || typeof markdown !== 'string') {
        return '<p>無効なマークダウンデータ</p>';
    }
    
    return markdown
        .replace(/^### (.+)$/gm, '<h4>$1</h4>')
        .replace(/^## (.+)$/gm, '<h3>$1</h3>')
        .replace(/^# (.+)$/gm, '<h2>$1</h2>')
        .replace(/^- (.+)$/gm, '<li>$1</li>')
        .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>')
        .replace(/\n/g, '<br>');
}
