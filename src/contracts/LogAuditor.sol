// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract LogAuditor {

    address public owner;

    struct BatchEntry {
        uint256 timestamp;      // Cuándo se subió el lote
        address auditor;
        uint256 logCount;       // Cuántos logs hay en este lote
        string batchRange;      // Metadatos: "Line 100-110" o "16:00-16:05"
        uint256 blockNumber;
    }

    // Mapping: ROOT (bytes32) => DATOS
    mapping(bytes32 => BatchEntry) public batches;

    // Lista de raíces para poder iterar
    bytes32[] public batchList;

    event BatchAnchored(bytes32 indexed merkleRoot, uint256 timestamp, uint256 logCount);

    modifier onlyOwner() {
        require(msg.sender == owner, "Acceso denegado.");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    // Guardar un LOTE (Root de Merkle) en lugar de log a log
    function saveBatchRoot(bytes32 _merkleRoot, uint256 _logCount, string memory _range) public onlyOwner {
        require(batches[_merkleRoot].timestamp == 0, "Error: Este lote ya esta registrado.");

        batches[_merkleRoot] = BatchEntry({
            timestamp: block.timestamp,
            auditor: msg.sender,
            logCount: _logCount,
            batchRange: _range,
            blockNumber: block.number
        });

        batchList.push(_merkleRoot);

        emit BatchAnchored(_merkleRoot, block.timestamp, _logCount);
    }

    // Verificar si una raíz de lote existe
    function verifyBatch(bytes32 _merkleRoot) public view returns (bool, uint256, uint256, string memory) {
        BatchEntry memory entry = batches[_merkleRoot];
        return (entry.timestamp > 0, entry.timestamp, entry.logCount, entry.batchRange);
    }

    function getTotalBatches() public view returns (uint256) {
        return batchList.length;
    }
}
