const fs = require('fs');
const html = fs.readFileSync('frontend/interview.html', 'utf8');
const scriptContent = html.match(/<script>([\s\S]*?)<\/script>/)[1];
try {
    new Function(scriptContent);
    console.log("Syntax is valid!");
} catch (e) {
    console.error("Syntax error:", e);
}
