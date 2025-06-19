// Simple test to simulate frontend queue behavior
const axios = require('axios');

const API_BASE = 'http://localhost:5001/api';

async function testQueueFlow() {
    const prospectId = 'e6cc756abfc098a3da4a430f22ee2bda';
    
    console.log('1. Starting queue test...');
    
    // Check initial queue status
    console.log('\n2. Initial queue status:');
    let status = await axios.get(`${API_BASE}/llm/queue/status`);
    console.log(JSON.stringify(status.data, null, 2));
    
    // Add item to queue
    console.log('\n3. Adding prospect to queue...');
    try {
        const response = await axios.post(`${API_BASE}/llm/enhance-single`, {
            prospect_id: prospectId,
            enhancement_type: 'all',
            user_id: 1
        });
        console.log('Queue response:', JSON.stringify(response.data, null, 2));
        
        const queueItemId = response.data.queue_item_id;
        
        // Check queue status immediately
        console.log('\n4. Queue status after adding:');
        status = await axios.get(`${API_BASE}/llm/queue/status`);
        console.log(JSON.stringify(status.data, null, 2));
        
        // Check specific item status
        console.log('\n5. Specific item status:');
        try {
            const itemStatus = await axios.get(`${API_BASE}/llm/queue/item/${queueItemId}`);
            console.log(JSON.stringify(itemStatus.data, null, 2));
        } catch (err) {
            console.log('Item not found or completed');
        }
        
        // Wait a moment and check again
        console.log('\n6. Waiting 3 seconds...');
        await new Promise(resolve => setTimeout(resolve, 3000));
        
        console.log('\n7. Queue status after waiting:');
        status = await axios.get(`${API_BASE}/llm/queue/status`);
        console.log(JSON.stringify(status.data, null, 2));
        
        // Try adding same item again (should be blocked)
        console.log('\n8. Trying to add same prospect again...');
        try {
            const response2 = await axios.post(`${API_BASE}/llm/enhance-single`, {
                prospect_id: prospectId,
                enhancement_type: 'all',
                user_id: 1
            });
            console.log('Second queue response:', JSON.stringify(response2.data, null, 2));
        } catch (err) {
            console.log('Error adding again:', err.response?.data || err.message);
        }
        
    } catch (error) {
        console.error('Error:', error.response?.data || error.message);
    }
}

testQueueFlow().catch(console.error);