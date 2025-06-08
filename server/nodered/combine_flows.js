const fs = require('fs');
const path = require('path');

const flowsDir = path.join(__dirname, 'flows');
const outputFile = path.join(__dirname, 'flow.json');

const combinedFlow = [];

fs.readdirSync(flowsDir).forEach(file => {
    if (path.extname(file) === '.json') {
        const filePath = path.join(flowsDir, file);
        const content = fs.readFileSync(filePath, 'utf8');
        const nodes = JSON.parse(content);
        combinedFlow.push(...nodes);
    }
});

fs.writeFileSync(outputFile, JSON.stringify(combinedFlow, null, 4));

console.log('✅ Combined all flows into flow.json'); 